"""Symon — OSC-controlled audio player for Raspberry Pi 3.

Listens for OSC messages and controls audio playback using pygame.mixer.

OSC Commands
------------
/symon/play  <filename|index>  Play a file from the audio directory.
                                Pass a filename (e.g. "cue1.wav") or a
                                1-based index from /symon/list.
/symon/stop                    Stop current playback.
/symon/pause                   Pause current playback.
/symon/resume                  Resume paused playback.
/symon/volume <0.0–1.0>        Set playback volume.
/symon/fade   [seconds]        Fade out over N seconds (default 2.0), then stop.
/symon/list                    Print file list; reply with newline-separated names.
/symon/status                  Reply with current playback status.

OSC Replies (sent when --reply-host is specified)
--------------------------------------------------
/symon/playing  <filename>            Playback started.
/symon/stopped  1                     Playback stopped.
/symon/paused   1                     Playback paused.
/symon/resumed  1                     Playback resumed.
/symon/volume   <float>               Volume acknowledged.
/symon/list     <newline-sep names>   File list.
/symon/status   <state> <file> <vol>  Current status.
/symon/error    <message>             Error description.
"""

import argparse
import os
import threading
import time
from pathlib import Path
from typing import Optional

try:
    import pygame
except ImportError:
    raise SystemExit(
        "pygame is required — run: pip install pygame  "
        "or: sudo apt install python3-pygame"
    )

# python-osc package imports as 'pythonosc'
from pythonosc import dispatcher, osc_server, udp_client


AUDIO_EXTENSIONS = {".wav", ".mp3", ".ogg", ".flac", ".aiff", ".aif"}
DEFAULT_PORT = 8000
DEFAULT_AUDIO_DIR = os.path.expanduser("~/audio")


class SymonPlayer:
    """OSC-controlled audio player backed by pygame.mixer."""

    def __init__(
        self,
        audio_dir: str,
        reply_host: str = "",
        reply_port: int = 9000,
    ):
        self._audio_dir = Path(audio_dir)
        self._reply_host = reply_host
        self._reply_port = reply_port
        self._lock = threading.Lock()
        self._volume: float = 1.0
        self._current_file: str = ""
        self._fade_thread: Optional[threading.Thread] = None
        self._fade_stop = threading.Event()

        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
        pygame.mixer.init()
        print(f"[symon] audio directory : {self._audio_dir}")
        print(f"[symon] pygame mixer    : {pygame.mixer.get_init()}")

    # ==== File helpers ====

    def _list_files(self) -> list:
        if not self._audio_dir.is_dir():
            return []
        return sorted(
            f.name
            for f in self._audio_dir.iterdir()
            if f.suffix.lower() in AUDIO_EXTENSIONS
        )

    def _resolve_file(self, name_or_index: str) -> Optional[Path]:
        """Resolve a filename or 1-based index string to a Path."""
        # Try as 1-based integer index
        try:
            idx = int(name_or_index) - 1
            files = self._list_files()
            if 0 <= idx < len(files):
                return self._audio_dir / files[idx]
        except (ValueError, TypeError):
            pass

        # Exact name match
        candidate = self._audio_dir / name_or_index
        if candidate.is_file():
            return candidate

        # Case-insensitive name match
        try:
            for f in self._audio_dir.iterdir():
                if f.name.lower() == str(name_or_index).lower():
                    return f
        except OSError:
            pass

        return None

    # ==== Reply helper ====

    def _reply(self, address: str, *args):
        """Send an OSC reply if a reply host is configured."""
        if not self._reply_host:
            return
        try:
            client = udp_client.SimpleUDPClient(self._reply_host, self._reply_port)
            client.send_message(address, list(args))
        except Exception as exc:
            print(f"[symon] reply error: {exc}")

    # ==== OSC handlers ====

    def handle_play(self, address, *args):
        name = str(args[0]).strip() if args else ""
        if not name:
            print("[symon] /play: no filename given")
            self._reply("/symon/error", "no filename given")
            return

        path = self._resolve_file(name)
        if path is None:
            print(f"[symon] /play: not found: {name!r}")
            self._reply("/symon/error", f"file not found: {name}")
            return

        with self._lock:
            self._stop_fade()
            try:
                pygame.mixer.music.load(str(path))
                pygame.mixer.music.set_volume(self._volume)
                pygame.mixer.music.play()
                self._current_file = path.name
                print(f"[symon] playing: {path.name}")
                self._reply("/symon/playing", path.name)
            except Exception as exc:
                print(f"[symon] playback error: {exc}")
                self._reply("/symon/error", str(exc))

    def handle_stop(self, address, *args):
        with self._lock:
            self._stop_fade()
            pygame.mixer.music.stop()
            self._current_file = ""
        print("[symon] stopped")
        self._reply("/symon/stopped", 1)

    def handle_pause(self, address, *args):
        with self._lock:
            pygame.mixer.music.pause()
        print("[symon] paused")
        self._reply("/symon/paused", 1)

    def handle_resume(self, address, *args):
        with self._lock:
            pygame.mixer.music.unpause()
        print("[symon] resumed")
        self._reply("/symon/resumed", 1)

    def handle_volume(self, address, *args):
        if not args:
            return
        try:
            vol = float(args[0])
        except (ValueError, TypeError):
            return
        vol = max(0.0, min(1.0, vol))
        with self._lock:
            self._volume = vol
            pygame.mixer.music.set_volume(vol)
        print(f"[symon] volume: {vol:.2f}")
        self._reply("/symon/volume", vol)

    def handle_fade(self, address, *args):
        seconds = 2.0
        if args:
            try:
                seconds = float(args[0])
            except (ValueError, TypeError):
                pass
        seconds = max(0.1, seconds)

        with self._lock:
            self._stop_fade()
            self._fade_stop.clear()
            start_vol = self._volume  # capture under lock to avoid a race
            t = threading.Thread(
                target=self._fade_worker, args=(seconds, start_vol), daemon=True
            )
            self._fade_thread = t
        t.start()
        print(f"[symon] fading out over {seconds:.1f}s")

    def _fade_worker(self, seconds: float, start_vol: float):
        steps = 20
        interval = seconds / steps
        for i in range(steps):
            if self._fade_stop.is_set():
                return
            vol = start_vol * (1.0 - (i + 1) / steps)
            with self._lock:
                pygame.mixer.music.set_volume(max(0.0, vol))
            time.sleep(interval)
        if not self._fade_stop.is_set():
            with self._lock:
                pygame.mixer.music.stop()
                pygame.mixer.music.set_volume(self._volume)
            print("[symon] fade complete")
            self._reply("/symon/stopped", 1)

    def _stop_fade(self):
        """Cancel any in-progress fade. Must be called with _lock held."""
        self._fade_stop.set()
        pygame.mixer.music.set_volume(self._volume)

    def handle_list(self, address, *args):
        files = self._list_files()
        payload = "\n".join(files) if files else "(empty)"
        print(f"[symon] {len(files)} file(s) in {self._audio_dir}:")
        for i, name in enumerate(files, 1):
            print(f"  {i:3d}. {name}")
        self._reply("/symon/list", payload)

    def handle_status(self, address, *args):
        busy = pygame.mixer.music.get_busy()
        state = "playing" if busy else "stopped"
        print(
            f"[symon] status: {state} | "
            f"file: {self._current_file!r} | "
            f"vol: {self._volume:.2f}"
        )
        self._reply("/symon/status", state, self._current_file, self._volume)


def build_dispatcher(player: SymonPlayer) -> dispatcher.Dispatcher:
    disp = dispatcher.Dispatcher()
    disp.map("/symon/play",   player.handle_play)
    disp.map("/symon/stop",   player.handle_stop)
    disp.map("/symon/pause",  player.handle_pause)
    disp.map("/symon/resume", player.handle_resume)
    disp.map("/symon/volume", player.handle_volume)
    disp.map("/symon/fade",   player.handle_fade)
    disp.map("/symon/list",   player.handle_list)
    disp.map("/symon/status", player.handle_status)
    return disp


def main():
    parser = argparse.ArgumentParser(
        description="Symon — OSC-controlled audio player for Raspberry Pi 3",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--port", type=int, default=DEFAULT_PORT,
        help="UDP port to listen for OSC messages",
    )
    parser.add_argument(
        "--audio-dir", default=DEFAULT_AUDIO_DIR,
        help="Directory containing audio files",
    )
    parser.add_argument(
        "--reply-host", default="",
        help="Host to send OSC status replies to (leave empty to disable replies)",
    )
    parser.add_argument(
        "--reply-port", type=int, default=9000,
        help="Port to send OSC status replies to",
    )
    args = parser.parse_args()

    player = SymonPlayer(
        audio_dir=args.audio_dir,
        reply_host=args.reply_host,
        reply_port=args.reply_port,
    )

    disp = build_dispatcher(player)
    server = osc_server.ThreadingOSCUDPServer(("0.0.0.0", args.port), disp)
    print(f"[symon] listening on 0.0.0.0:{args.port}")
    print("[symon] press Ctrl-C to stop")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[symon] shutting down")
    finally:
        pygame.mixer.quit()


if __name__ == "__main__":
    main()
