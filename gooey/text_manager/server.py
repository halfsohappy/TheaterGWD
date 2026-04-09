"""
Flask web server for the annieData Text Manager.

Serves a web UI that lets you browse, filter, edit, and apply changes
to all user-facing text in the annieData Control Center.
"""

import json
import os
from dataclasses import asdict

from flask import Flask, jsonify, render_template, request

from .extractor import apply_edits, scan_all

_gooey_dir: str = ""
_entries_cache: list = []


def create_app(gooey_dir: str) -> Flask:
    """Create and configure the Text Manager Flask application."""
    global _gooey_dir
    _gooey_dir = gooey_dir

    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
        static_folder=os.path.join(gooey_dir, "app", "static"),
        static_url_path="/static",
    )

    @app.route("/")
    def index():
        return render_template("editor.html")

    @app.route("/api/scan", methods=["POST"])
    def api_scan():
        """(Re)scan all frontend files and return text entries."""
        global _entries_cache
        _entries_cache = scan_all(_gooey_dir)
        return jsonify({
            "status": "ok",
            "count": len(_entries_cache),
            "entries": [asdict(e) for e in _entries_cache],
        })

    @app.route("/api/entries", methods=["GET"])
    def api_entries():
        """Return the cached text entries (call /api/scan first)."""
        return jsonify({
            "status": "ok",
            "count": len(_entries_cache),
            "entries": [asdict(e) for e in _entries_cache],
        })

    @app.route("/api/apply", methods=["POST"])
    def api_apply():
        """Apply text edits back to source files."""
        data = request.get_json(force=True)
        edits = data.get("edits", {})
        if not edits:
            return jsonify({"status": "ok", "applied": 0, "skipped": 0, "errors": []})
        result = apply_edits(edits, _gooey_dir)
        # Re-scan after applying
        global _entries_cache
        _entries_cache = scan_all(_gooey_dir)
        result["new_count"] = len(_entries_cache)
        result["status"] = "ok"
        return jsonify(result)

    @app.route("/api/file/<path:filepath>")
    def api_file(filepath):
        """Return the raw content of a source file (for preview)."""
        abs_path = os.path.join(_gooey_dir, filepath)
        if not os.path.isfile(abs_path):
            return jsonify({"status": "error", "message": "File not found"}), 404
        with open(abs_path, encoding="utf-8") as f:
            content = f.read()
        return jsonify({"status": "ok", "content": content})

    @app.route("/api/preview", methods=["POST"])
    def api_preview():
        """Return an HTML fragment for previewing text in context."""
        data = request.get_json(force=True)
        file_path = data.get("file", "")
        line = data.get("line", 0)
        text = data.get("text", "")
        replacement = data.get("replacement", text)

        abs_path = os.path.join(_gooey_dir, file_path)
        if not os.path.isfile(abs_path):
            return jsonify({"status": "error", "html": "<em>File not found</em>"})

        with open(abs_path, encoding="utf-8") as f:
            lines = f.readlines()

        # Get a window of lines around the target
        lo = max(0, line - 6)
        hi = min(len(lines), line + 5)
        snippet_lines = lines[lo:hi]

        # Highlight the target text in the snippet
        preview_lines = []
        for i, ln in enumerate(snippet_lines, start=lo + 1):
            ln_html = ln.rstrip("\n")
            # Escape HTML
            ln_html = ln_html.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            if i == line and text in lines[line - 1]:
                escaped_text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                escaped_repl = replacement.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                if replacement != text:
                    ln_html = ln_html.replace(
                        escaped_text,
                        f'<del style="background:#fdd;text-decoration:line-through">{escaped_text}</del>'
                        f'<ins style="background:#dfd;text-decoration:none">{escaped_repl}</ins>'
                    )
                else:
                    ln_html = ln_html.replace(
                        escaped_text,
                        f'<mark style="background:#fff3b0">{escaped_text}</mark>'
                    )
            prefix = f'<span style="color:#888;user-select:none">{i:>4} </span>'
            preview_lines.append(prefix + ln_html)

        html = '<pre style="font-family:\'Martian Mono\',monospace;font-size:12px;line-height:1.5;margin:0;overflow-x:auto">' + "\n".join(preview_lines) + "</pre>"
        return jsonify({"status": "ok", "html": html})

    return app


def run(gooey_dir: str, port: int = 5001, debug: bool = True):
    """Start the Text Manager web server."""
    app = create_app(gooey_dir)

    # Auto-scan on startup
    global _entries_cache
    _entries_cache = scan_all(gooey_dir)
    print(f"\n  ✦ Text Manager: found {len(_entries_cache)} text entries")
    print(f"  ✦ Open http://127.0.0.1:{port} to start editing\n")

    app.run(host="127.0.0.1", port=port, debug=debug)
