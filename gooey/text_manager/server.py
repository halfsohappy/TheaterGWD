"""
Flask web server for the annieData Text Manager.

Serves a web UI that lets you browse, filter, edit, and apply changes
to all user-facing text in the annieData Control Center.
"""

import json
import os
import re
from dataclasses import asdict

from flask import Flask, jsonify, render_template, request

from .extractor import apply_edits, scan_all

# ---------------------------------------------------------------------------
# Fragment rendering helpers
# ---------------------------------------------------------------------------

_JINJA_VAR_RE = re.compile(r'\{\{[^}]*\}\}')
_JINJA_BLOCK_RE = re.compile(r'\{%-?[^%]*-?%\}')
# Use [^>]*> to match closing tags with any attributes/whitespace (e.g. </script >, </script\ttype>).
_SCRIPT_BLOCK_RE = re.compile(r'<script\b[^>]*?>.*?</script[^>]*>', re.DOTALL | re.IGNORECASE)

# How many lines to walk back from the target when looking for a container.
_CONTAINER_SEARCH_START = 5
_CONTAINER_SEARCH_DEPTH = 50
# Maximum number of source lines included in one fragment.
_FRAGMENT_MAX_LINES = 44

# Patterns that indicate a structural container worth using as viewport root.
_CONTAINER_PAT = re.compile(
    r'class="card(?:\s|")|class="welcome-banner|class="form-row\b|'
    r'class="bulk-action-row|class="modal-content|class="onboard|'
    r'class="msg-scene-filter|class="hdr-content|class="dev-dropdown|'
    r'<section\b',
    re.IGNORECASE,
)

# Inline CSS for the simulated-element previews used by JS entries.
_JS_PREVIEW_CSS = (
    'body{margin:16px;background:#f6f4fb;font-family:system-ui,sans-serif;}'
    '.preview-wrap{display:flex;flex-direction:column;gap:12px;}'
)


def _strip_jinja(line: str) -> str:
    """Remove Jinja2 directives and replace variables with a placeholder."""
    line = _JINJA_BLOCK_RE.sub('', line)
    line = _JINJA_VAR_RE.sub(
        '<span class="tm-jinja">[…]</span>', line
    )
    return line


def _build_html_fragment(all_lines: list, entry, replacement, base_url: str = '') -> str:
    """Return a srcdoc-ready HTML document built from the entry's source file."""
    n = len(all_lines)
    target_idx = entry.line - 1  # 0-based

    # Walk backward to find the nearest enclosing structural container.
    lo = max(0, target_idx - _CONTAINER_SEARCH_START)
    for i in range(target_idx, max(-1, target_idx - _CONTAINER_SEARCH_DEPTH), -1):
        if _CONTAINER_PAT.search(all_lines[i]):
            lo = i
            break

    hi = min(n, lo + _FRAGMENT_MAX_LINES)

    # Process each line: strip Jinja2, then highlight the target line.
    target_text = entry.text
    repl_text = replacement if replacement is not None else target_text
    is_modified = repl_text != target_text

    esc_t = target_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    esc_r = repl_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    fragment_parts = []
    for i in range(lo, hi):
        raw = all_lines[i].rstrip('\n')
        processed = _strip_jinja(raw)

        if i == target_idx and target_text:
            if is_modified:
                mark = (
                    f'<del class="tm-del">{esc_t}</del>'
                    f'<ins class="tm-ins">{esc_r}</ins>'
                )
            else:
                mark = f'<mark class="tm-hl">{esc_t}</mark>'

            # Try replacing raw text first, then HTML-escaped form.
            if target_text in processed:
                processed = processed.replace(target_text, mark, 1)
            elif esc_t != target_text and esc_t in processed:
                processed = processed.replace(esc_t, mark, 1)
            else:
                # Fallback: highlight the entire line.
                processed = '<div class="tm-line-hl">' + processed + '</div>'

        fragment_parts.append(processed)

    fragment = '\n'.join(fragment_parts)
    fragment = _SCRIPT_BLOCK_RE.sub('', fragment)
    return _wrap_srcdoc(fragment, base_url=base_url)


def _build_js_fragment(entry, replacement, base_url: str = '') -> str:
    """Return a srcdoc-ready HTML document simulating a JS-injected element."""
    text = replacement if replacement is not None else entry.text
    el = entry.element_info.lower()
    esc = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    if 'toast' in el or 'showtoast' in el:
        body = (
            '<div style="background:#e8f0fe;color:#1967d2;border:1px solid #c5d9f7;'
            'border-radius:8px;padding:10px 16px;font-size:13px;font-weight:500;'
            'box-shadow:0 4px 12px rgba(0,0,0,.15);display:inline-block">'
            + esc + '</div>'
        )
    elif 'confirm' in el:
        body = (
            '<div style="border:1px solid #e0dae8;border-radius:8px;padding:16px;'
            'background:#fff;max-width:320px">'
            '<p style="margin:0 0 12px;font-size:14px">' + esc + '</p>'
            '<div style="display:flex;gap:8px">'
            '<button style="padding:5px 14px;background:#7c5cbf;color:#fff;border:none;border-radius:4px">OK</button>'
            '<button style="padding:5px 14px;background:#f0ecf7;border:1px solid #e0dae8;border-radius:4px">Cancel</button>'
            '</div></div>'
        )
    elif 'textcontent' in el or 'innerhtml' in el or 'innertext' in el:
        body = '<p style="font-size:14px;color:#1a1a2e;line-height:1.5">' + esc + '</p>'
    elif 'tour_step' in el or 'tour' in el:
        body = (
            '<div style="background:#fff;border:1px solid #e0dae8;border-radius:8px;'
            'padding:16px;max-width:300px">'
            '<p style="font-size:13px;color:#1a1a2e;margin:0">' + esc + '</p></div>'
        )
    elif 'label' in el or 'hint' in el:
        body = '<label style="font-size:13px;font-weight:500;color:#1a1a2e">' + esc + '</label>'
    else:
        body = '<div style="font-size:13px;color:#1a1a2e">' + esc + '</div>'

    return _wrap_srcdoc(
        '<div class="preview-wrap">' + body + '</div>',
        base_url=base_url,
        extra_css=_JS_PREVIEW_CSS,
    )


def _wrap_srcdoc(fragment: str, base_url: str = '', extra_css: str = '') -> str:
    """Wrap an HTML fragment in a full srcdoc document with the app's CSS."""
    base_tag = f'<base href="{base_url}">' if base_url else ''
    return (
        '<!DOCTYPE html><html><head>'
        '<meta charset="UTF-8">'
        + base_tag
        + '<link rel="stylesheet" href="/static/css/style.css">'
        '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css">'
        '<style>'
        'html,body{margin:0;padding:8px;background:var(--bg,#f6f4fb);}'
        '.tm-hl{background:#fff3b0!important;outline:2px solid #e8a820;border-radius:2px;}'
        '.tm-del{background:#fdd;text-decoration:line-through;border-radius:2px;}'
        '.tm-ins{background:#dfd;text-decoration:none;border-radius:2px;}'
        '.tm-jinja{color:#bbb;font-style:italic;font-size:11px;}'
        '.tm-line-hl{background:#fff3b0;outline:1px solid #e8a820;display:block;}'
        + extra_css
        + '</style>'
        # allow-scripts enables the scroll-to-highlight helper.  allow-same-origin
        # is intentionally omitted — CSS loads via the <base> absolute URL without
        # needing same-origin access, and the script only calls scrollIntoView.
        '<script>window.addEventListener("load",function(){'
        'var e=document.querySelector(".tm-hl,.tm-del,.tm-ins,.tm-line-hl");'
        'if(e)e.scrollIntoView({block:"center"});'
        '});</script>'
        '</head><body>'
        + fragment
        + '</body></html>'
    )

# Allowlisted relative paths that the tool is permitted to read/write.
# Only files within these directories (under gooey/) are accessible.
_SAFE_PREFIXES = ("app/templates/", "app/static/js/", "app/static/css/")


def _safe_resolve(gooey_dir: str, rel_path: str):
    """Resolve *rel_path* to an absolute path, rejecting traversal attacks.

    Returns the resolved absolute path, or ``None`` if the path escapes
    the gooey directory or is not under an allowlisted prefix.
    """
    # Normalise and reject obvious traversal
    normed = os.path.normpath(rel_path)
    if normed.startswith("..") or os.path.isabs(normed):
        return None
    abs_path = os.path.realpath(os.path.join(gooey_dir, normed))
    real_gooey = os.path.realpath(gooey_dir)
    if not abs_path.startswith(real_gooey + os.sep):
        return None
    # Must be under one of the safe prefixes
    if not any(normed.startswith(p) for p in _SAFE_PREFIXES):
        return None
    return abs_path

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
        abs_path = _safe_resolve(_gooey_dir, filepath)
        if abs_path is None or not os.path.isfile(abs_path):
            return jsonify({"status": "error", "message": "File not found"}), 404
        with open(abs_path, encoding="utf-8") as f:
            content = f.read()
        return jsonify({"status": "ok", "content": content})

    @app.route("/api/fragment", methods=["POST"])
    def api_fragment():
        """Return a srcdoc-ready HTML document for a gallery viewport."""
        data = request.get_json(force=True)
        entry_id = data.get("id", "")
        replacement = data.get("replacement", None)

        entry = next((e for e in _entries_cache if e.id == entry_id), None)
        if not entry:
            return jsonify({"status": "error", "html": ""})

        # Derive the base URL from the current request so the srcdoc's <base>
        # tag points at the correct host regardless of configured port.
        base_url = request.host_url  # e.g. "http://127.0.0.1:5001/"

        if entry.source_type == "js":
            html_doc = _build_js_fragment(entry, replacement, base_url=base_url)
            return jsonify({"status": "ok", "html": html_doc})

        abs_path = _safe_resolve(_gooey_dir, entry.file)
        if not abs_path or not os.path.isfile(abs_path):
            return jsonify({"status": "error", "html": ""})

        with open(abs_path, encoding="utf-8") as f:
            all_lines = f.readlines()

        html_doc = _build_html_fragment(all_lines, entry, replacement, base_url=base_url)
        return jsonify({"status": "ok", "html": html_doc})

    @app.route("/api/preview", methods=["POST"])
    def api_preview():
        """Return an HTML fragment for previewing text in context."""
        data = request.get_json(force=True)
        file_path = data.get("file", "")
        line = data.get("line", 0)
        text = data.get("text", "")
        replacement = data.get("replacement", text)

        abs_path = _safe_resolve(_gooey_dir, file_path)
        if abs_path is None or not os.path.isfile(abs_path):
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


def run(gooey_dir: str, port: int = 5001, debug: bool = False):
    """Start the Text Manager web server."""
    app = create_app(gooey_dir)

    # Auto-scan on startup
    global _entries_cache
    _entries_cache = scan_all(gooey_dir)
    print(f"\n  ✦ Text Manager: found {len(_entries_cache)} text entries")
    print(f"  ✦ Open http://127.0.0.1:{port} to start editing\n")

    app.run(host="127.0.0.1", port=port, debug=debug)
