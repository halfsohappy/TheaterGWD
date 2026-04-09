"""
Text extraction engine for annieData Control Center.

Scans HTML templates and JavaScript source files, extracts every piece of
user-facing text, and assigns overlapping categories so the user can filter,
edit, and apply changes back to the source files.
"""

import hashlib
import os
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import List, Optional


# ---------------------------------------------------------------------------
#  Configuration constants
# ---------------------------------------------------------------------------

# Strings shorter than this are ignored (skips punctuation, single chars, etc.)
MIN_TEXT_LEN = 2

# How many lines to walk backwards when detecting which app section a line
# belongs to (Messages, Scenes, Ori, etc.).
SECTION_LOOKBACK_LINES = 200

# When the exact line reported by the parser doesn't contain the expected text,
# try these offsets (in order) before giving up.  Parser positions can be off
# by a line or two for multiline elements.
ADJACENT_LINE_OFFSETS = [-1, 1, -2, 2]


# ---------------------------------------------------------------------------
#  Data structures
# ---------------------------------------------------------------------------

@dataclass
class TextEntry:
    """One user-facing string found in a source file."""

    id: str                      # deterministic hash (file + line + text)
    text: str                    # original text content
    file: str                    # source path relative to gooey/
    line: int                    # 1-based line number
    col: int                     # 0-based column within the line
    line_content: str            # full source line (for safe replacement)
    context: str                 # surrounding 2-line window
    source_type: str             # "html" or "js"
    element_info: str            # e.g. "button", "placeholder", "title attr"
    categories: List[str] = field(default_factory=list)
    section: str = ""            # app section: messages, scenes, ori, …
    parent_tag: str = ""         # nearest parent tag (for HTML entries)


def _make_id(file: str, line: int, text: str) -> str:
    raw = f"{file}:{line}:{text}"
    return hashlib.sha1(raw.encode()).hexdigest()[:12]


def _context_window(lines: List[str], idx: int, window: int = 2) -> str:
    lo = max(0, idx - window)
    hi = min(len(lines), idx + window + 1)
    return "\n".join(lines[lo:hi])


# ---------------------------------------------------------------------------
#  Category helpers
# ---------------------------------------------------------------------------

# Primary category assigned by element / attribute type
_ELEMENT_CATEGORIES = {
    "button":        "Buttons & Actions",
    "a":             "Buttons & Actions",
    "h1":            "Headings & Titles",
    "h2":            "Headings & Titles",
    "h3":            "Headings & Titles",
    "h4":            "Headings & Titles",
    "h5":            "Headings & Titles",
    "h6":            "Headings & Titles",
    "label":         "Form Labels",
    "th":            "Table Headers",
    "option":        "Options & Dropdowns",
    "optgroup":      "Options & Dropdowns",
    "summary":       "Headings & Titles",
    "p":             "Descriptions & Help Text",
    "span":          "Descriptions & Help Text",
    "td":            "Descriptions & Help Text",
    "div":           "Descriptions & Help Text",
    "strong":        "Descriptions & Help Text",
    "em":            "Descriptions & Help Text",
}

_ATTR_CATEGORIES = {
    "placeholder":  "Placeholder Text",
    "title":        "Tooltip & Hover Text",
    "aria-label":   "Tooltip & Hover Text",
    "alt":          "Tooltip & Hover Text",
}

# Section detected by scanning backwards from the text entry's line until one
# of these patterns matches.  Each pattern targets the HTML section ID, comment
# banner, or characteristic element IDs that mark that section.
_SECTION_MARKERS = [
    (r"sec-messages|MESSAGES|msgTable|msgName|Create.*Edit.*Message",   "Messages"),
    (r"sec-scenes|SCENES|sceneTable|sceneName|Create.*Edit.*Scene",    "Scenes"),
    (r"sec-ori|ORI|oriTable|oriName|Orientation",                      "Ori"),
    (r"sec-shows|SHOWS|showSaveName|Query.*Device.*Shows",             "Shows"),
    (r"sec-advanced|ADVANCED|Raw.*OSC|Bridge|imu-cal",                 "Advanced"),
    (r"sec-script|PYTHON|scriptEditor|Python",                         "Python"),
    (r"sec-direct|DIRECT|directSensor",                                "Direct"),
    (r"panelRight|viewFeed|viewSerial|viewReference|viewNotifications", "Panels"),
    (r"devSettingsModal|deviceConfigModal|tareModal|confirmModal",      "Modals"),
    (r"welcomeBanner|onboard",                                          "Tour & Onboarding"),
]

# Content-based secondary categories
_CONTENT_KEYWORDS = {
    "Ori-Related":      [r"\bori\b", r"orientation", r"quaternion", r"swing.?twist", r"euler"],
    "Scene-Related":    [r"\bscene\b", r"streaming", r"\bperiod\b"],
    "Sensor Labels":    [r"accel", r"gyro", r"baro", r"magnetom", r"sensor", r"quaternion",
                         r"limb", r"twist", r"azimuth", r"tilt", r"pitch", r"roll", r"yaw"],
    "Gate & Conditions": [r"\bgate\b", r"trigger", r"threshold", r"rising", r"falling", r"toggle"],
    "Tour & Onboarding": [r"\btour\b", r"welcome", r"step\s*\d", r"onboard"],
    "Error Messages":   [r"required", r"invalid", r"failed", r"error", r"cannot"],
    "Status Messages":  [r"connect", r"disconnect", r"listening", r"running"],
    "Empty States":     [r"no\s+(messages|scenes|ori|shows|items|notifications)",
                         r"not\s+yet", r"empty"],
    "API Reference":    [r"sensor\(", r"osc_send", r"device\.", r"clamp\(", r"remap\("],
}


def _detect_section(lines: List[str], line_idx: int) -> str:
    """Walk backwards to find the nearest section marker."""
    for i in range(line_idx, max(-1, line_idx - SECTION_LOOKBACK_LINES), -1):
        if i < 0:
            break
        line = lines[i]
        for pattern, section in _SECTION_MARKERS:
            if re.search(pattern, line, re.IGNORECASE):
                return section
    return "General"


def _categorize(entry: TextEntry, lines: List[str]) -> None:
    """Assign overlapping categories to a TextEntry in-place."""
    cats = set()

    # Primary category from element type
    el = entry.element_info.lower()
    if el.startswith("attr:"):
        attr_name = el.split(":", 1)[1]
        if attr_name in _ATTR_CATEGORIES:
            cats.add(_ATTR_CATEGORIES[attr_name])
    elif el in _ELEMENT_CATEGORIES:
        cats.add(_ELEMENT_CATEGORIES[el])

    # JS-specific categories
    if entry.source_type == "js":
        if "toast" in el or "showtoast" in el:
            cats.add("Notification & Toast Text")
        elif "confirm" in el or "showconfirm" in el:
            cats.add("Confirmation Dialogs")
        elif "textcontent" in el or "innerhtml" in el:
            cats.add("Dynamic Text (JS)")
        elif "tour_step" in el:
            cats.add("Tour & Onboarding")
        elif "sensor_cat" in el:
            cats.add("Sensor Labels")
        elif ".label" in el or ".hint" in el:
            cats.add("Sensor Labels")

    # Content-based secondary categories
    text_lower = entry.text.lower()
    for cat_name, patterns in _CONTENT_KEYWORDS.items():
        for pat in patterns:
            if re.search(pat, text_lower, re.IGNORECASE):
                cats.add(cat_name)
                break

    # Section
    entry.section = _detect_section(lines, entry.line - 1)

    # Hint text
    if "hint" in entry.line_content.lower() or "hint-text" in entry.line_content:
        cats.add("Descriptions & Help Text")

    # Empty state
    if "empty-state" in entry.line_content or "empty-text" in entry.line_content:
        cats.add("Empty States")

    # Modal context
    if "modal" in entry.line_content.lower() or entry.section == "Modals":
        cats.add("Modal Text")

    # Ensure at least one category
    if not cats:
        cats.add("Other Text")

    entry.categories = sorted(cats)


# ---------------------------------------------------------------------------
#  HTML extraction
# ---------------------------------------------------------------------------

# Attributes that contain user-visible text
_TEXT_ATTRS = {"placeholder", "title", "aria-label", "alt"}

# Tags whose text content is typically user-visible
_VISIBLE_TAGS = {
    "button", "label", "h1", "h2", "h3", "h4", "h5", "h6",
    "p", "span", "td", "th", "option", "summary", "strong", "em",
    "a",
}

# Tags to skip entirely
_SKIP_TAGS = {"script", "style", "code", "pre", "textarea"}


class _HTMLTextParser(HTMLParser):
    """Custom HTML parser that extracts user-facing text with positions."""

    def __init__(self, filepath: str, raw_lines: List[str]):
        super().__init__(convert_charrefs=True)
        self.filepath = filepath
        self.raw_lines = raw_lines
        self.entries: List[TextEntry] = []
        self._tag_stack: List[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs):
        tag = tag.lower()
        self._tag_stack.append(tag)

        if tag in _SKIP_TAGS:
            self._skip_depth += 1
            return

        if self._skip_depth > 0:
            return

        attrs_dict = dict(attrs)

        # Extract text attributes
        for attr_name in _TEXT_ATTRS:
            val = attrs_dict.get(attr_name, "").strip()
            if val and len(val) >= MIN_TEXT_LEN:
                # Skip Jinja2 template expressions
                if val.startswith("{{") or val.startswith("{%"):
                    continue
                line, _ = self.getpos()
                line_content = self.raw_lines[line - 1] if line <= len(self.raw_lines) else ""
                col = line_content.find(val)
                self.entries.append(TextEntry(
                    id=_make_id(self.filepath, line, val),
                    text=val,
                    file=self.filepath,
                    line=line,
                    col=max(0, col),
                    line_content=line_content,
                    context=_context_window(self.raw_lines, line - 1),
                    source_type="html",
                    element_info=f"attr:{attr_name}",
                    parent_tag=tag,
                ))

        # Extract optgroup label
        if tag == "optgroup" and "label" in attrs_dict:
            label = attrs_dict["label"].strip()
            if label and len(label) >= MIN_TEXT_LEN:
                line, _ = self.getpos()
                line_content = self.raw_lines[line - 1] if line <= len(self.raw_lines) else ""
                col = line_content.find(label)
                self.entries.append(TextEntry(
                    id=_make_id(self.filepath, line, label),
                    text=label,
                    file=self.filepath,
                    line=line,
                    col=max(0, col),
                    line_content=line_content,
                    context=_context_window(self.raw_lines, line - 1),
                    source_type="html",
                    element_info="optgroup",
                    parent_tag="optgroup",
                ))

    def handle_endtag(self, tag: str):
        tag = tag.lower()
        if tag in _SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        if self._tag_stack and self._tag_stack[-1] == tag:
            self._tag_stack.pop()

    def handle_data(self, data: str):
        if self._skip_depth > 0:
            return

        text = data.strip()
        if not text or len(text) < MIN_TEXT_LEN:
            return

        # Skip Jinja2 expressions
        if text.startswith("{{") or text.startswith("{%"):
            return

        # Skip pure whitespace / newlines
        if not text.replace("\n", "").replace("\r", "").strip():
            return

        # Determine parent tag
        parent = self._tag_stack[-1] if self._tag_stack else "body"

        # Only extract text from visible elements
        if parent in _SKIP_TAGS:
            return

        line, _ = self.getpos()
        line_content = self.raw_lines[line - 1] if line <= len(self.raw_lines) else ""
        col = line_content.find(text[:30])  # find start of text in line

        self.entries.append(TextEntry(
            id=_make_id(self.filepath, line, text),
            text=text,
            file=self.filepath,
            line=line,
            col=max(0, col),
            line_content=line_content,
            context=_context_window(self.raw_lines, line - 1),
            source_type="html",
            element_info=parent,
            parent_tag=parent,
        ))


def _preprocess_jinja(content: str) -> str:
    """Replace Jinja2 template tags with safe placeholders for HTML parsing."""
    # Replace {{ ... }} with a visible placeholder
    content = re.sub(r"\{\{.*?\}\}", "TMPL", content)
    # Replace {% ... %} blocks
    content = re.sub(r"\{%.*?%\}", "", content)
    return content


def extract_html(filepath: str, base_dir: str) -> List[TextEntry]:
    """Extract user-facing text from an HTML template file."""
    with open(filepath, encoding="utf-8") as f:
        raw_content = f.read()

    raw_lines = raw_content.split("\n")
    rel_path = os.path.relpath(filepath, base_dir)

    # Pre-process for Jinja2 but keep line structure intact
    processed = _preprocess_jinja(raw_content)

    parser = _HTMLTextParser(rel_path, raw_lines)
    try:
        parser.feed(processed)
    except Exception:
        pass  # partial parse is still useful

    # Filter out noise
    entries = []
    seen = set()
    for e in parser.entries:
        # Skip very short or purely numeric/symbolic text
        cleaned = e.text.strip()
        if len(cleaned) < MIN_TEXT_LEN:
            continue
        if re.match(r"^[\d.,:;!?@#$%^&*()\-+=<>/\\|~`\[\]{}]+$", cleaned):
            continue
        # Skip duplicate entries on the same line
        key = (e.file, e.line, cleaned[:50])
        if key in seen:
            continue
        seen.add(key)
        # Assign categories
        _categorize(e, raw_lines)
        entries.append(e)

    return entries


# ---------------------------------------------------------------------------
#  JavaScript extraction
# ---------------------------------------------------------------------------

def _extract_js_strings(filepath: str, base_dir: str) -> List[TextEntry]:
    """Extract user-facing strings from a JavaScript file."""
    with open(filepath, encoding="utf-8") as f:
        raw_content = f.read()

    raw_lines = raw_content.split("\n")
    rel_path = os.path.relpath(filepath, base_dir)
    entries: List[TextEntry] = []
    seen: set = set()

    def _add(text: str, line_idx: int, element_info: str):
        text = text.strip()
        if len(text) < MIN_TEXT_LEN:
            return
        # Skip strings that look like selectors, IDs, CSS classes, or code
        if text.startswith("#") or text.startswith(".") or text.startswith("bi-"):
            return
        if re.match(r"^[a-zA-Z_$][\w$]*$", text):
            return  # single identifier
        if text.startswith("http") or text.startswith("/api/"):
            return  # URLs
        if text.startswith("gooey_") or text.startswith("gooey-"):
            return  # localStorage keys
        # Deduplicate
        key = (rel_path, line_idx + 1, text[:50])
        if key in seen:
            return
        seen.add(key)

        line_content = raw_lines[line_idx] if line_idx < len(raw_lines) else ""
        col = line_content.find(text[:30])
        entry = TextEntry(
            id=_make_id(rel_path, line_idx + 1, text),
            text=text,
            file=rel_path,
            line=line_idx + 1,
            col=max(0, col),
            line_content=line_content,
            context=_context_window(raw_lines, line_idx),
            source_type="js",
            element_info=element_info,
        )
        _categorize(entry, raw_lines)
        entries.append(entry)

    # Pattern 1: TOUR_STEPS array — title and body properties
    _extract_js_object_array(
        raw_lines, rel_path, entries, seen,
        r"TOUR_STEPS",
        ["title", "body"],
        "tour_step",
    )

    # Pattern 2: SENSOR_CATEGORIES array — label and hint properties
    _extract_js_object_array(
        raw_lines, rel_path, entries, seen,
        r"SENSOR_CATEGORIES",
        ["label", "hint"],
        "sensor_cat",
    )

    for i, line in enumerate(raw_lines):
        stripped = line.strip()

        # Skip comments
        if stripped.startswith("//") or stripped.startswith("/*"):
            continue

        # Pattern 3: .textContent = "..."
        m = re.search(r'\.textContent\s*=\s*["\']([^"\']+)["\']', line)
        if m:
            _add(m.group(1), i, "textContent")

        # Pattern 4: .innerHTML assignments with quoted strings
        # (only simple ones, not full HTML templates)
        m = re.search(r'\.innerHTML\s*=\s*["\']([^"\']{3,})["\']', line)
        if m and "<" not in m.group(1):
            _add(m.group(1), i, "innerHTML")

        # Pattern 5: toast("...", ...) or showToast("...", ...)
        for pat in [r'toast\(\s*["\']([^"\']+)["\']',
                    r'showToast\(\s*["\']([^"\']+)["\']']:
            m = re.search(pat, line)
            if m:
                _add(m.group(1), i, "toast")

        # Pattern 6: showConfirm("title", "body", ...)
        m = re.search(
            r'showConfirm\(\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']+)["\']',
            line
        )
        if m:
            _add(m.group(1), i, "showConfirm.title")
            _add(m.group(2), i, "showConfirm.body")

        # Pattern 7: toast with string concatenation: toast("prefix" + var ...)
        m = re.search(r'toast\(\s*["\']([^"\']{4,})["\']', line)
        if m:
            _add(m.group(1), i, "toast")

        # Pattern 8: Inline object properties — label, hint, title, body, text, name
        for prop in ["label", "hint", "title", "body", "text", "name",
                     "placeholder", "okLabel"]:
            m = re.search(
                rf'(?:^|\s|,){prop}\s*:\s*["\']([^"\']+)["\']', line
            )
            if m:
                val = m.group(1)
                # Skip if it looks like a selector or ID
                if len(val) >= MIN_TEXT_LEN and not val.startswith("#"):
                    _add(val, i, f"prop:{prop}")

    return entries


def _extract_js_object_array(
    raw_lines: List[str],
    rel_path: str,
    entries: List[TextEntry],
    seen: set,
    array_name: str,
    prop_names: List[str],
    element_prefix: str,
) -> None:
    """Extract string properties from a known JS array of objects."""
    in_array = False
    brace_depth = 0

    for i, line in enumerate(raw_lines):
        if not in_array:
            if re.search(rf"\b{array_name}\s*=\s*\[", line):
                in_array = True
                brace_depth = line.count("[") - line.count("]")
            continue

        brace_depth += line.count("[") - line.count("]")
        if brace_depth <= 0:
            break

        for prop in prop_names:
            m = re.search(rf'{prop}\s*:\s*["\']([^"\']+)["\']', line)
            if m:
                text = m.group(1).strip()
                if len(text) >= MIN_TEXT_LEN:
                    key = (rel_path, i + 1, text[:50])
                    if key not in seen:
                        seen.add(key)
                        line_content = raw_lines[i]
                        col = line_content.find(text[:30])
                        entry = TextEntry(
                            id=_make_id(rel_path, i + 1, text),
                            text=text,
                            file=rel_path,
                            line=i + 1,
                            col=max(0, col),
                            line_content=line_content,
                            context=_context_window(raw_lines, i),
                            source_type="js",
                            element_info=f"{element_prefix}.{prop}",
                        )
                        _categorize(entry, raw_lines)
                        entries.append(entry)


# ---------------------------------------------------------------------------
#  Public API
# ---------------------------------------------------------------------------

def scan_all(gooey_dir: str) -> List[TextEntry]:
    """Scan all frontend files and return extracted text entries."""
    entries: List[TextEntry] = []

    html_files = [
        os.path.join(gooey_dir, "app", "templates", "index.html"),
        os.path.join(gooey_dir, "app", "templates", "remote.html"),
        os.path.join(gooey_dir, "app", "templates", "docs.html"),
    ]

    js_files = [
        os.path.join(gooey_dir, "app", "static", "js", "app.js"),
        os.path.join(gooey_dir, "app", "static", "js", "remote.js"),
    ]

    for fp in html_files:
        if os.path.isfile(fp):
            entries.extend(extract_html(fp, gooey_dir))

    for fp in js_files:
        if os.path.isfile(fp):
            entries.extend(_extract_js_strings(fp, gooey_dir))

    return entries


def apply_edits(edits: dict, gooey_dir: str) -> dict:
    """
    Apply text edits back to source files.

    Parameters
    ----------
    edits : dict
        Mapping of entry ID → {"file": str, "line": int,
        "original": str, "replacement": str}
    gooey_dir : str
        Root of the gooey directory.

    Returns
    -------
    dict  {"applied": int, "skipped": int, "errors": list[str]}
    """
    # Group edits by file
    by_file: dict = {}
    for eid, edit in edits.items():
        fp = edit["file"]
        by_file.setdefault(fp, []).append(edit)

    applied = 0
    skipped = 0
    errors: List[str] = []

    for rel_path, file_edits in by_file.items():
        abs_path = os.path.join(gooey_dir, rel_path)
        if not os.path.isfile(abs_path):
            errors.append(f"File not found: {rel_path}")
            skipped += len(file_edits)
            continue

        with open(abs_path, encoding="utf-8") as f:
            lines = f.read().split("\n")

        # Sort edits by line number (descending) so replacements
        # don't shift later line numbers
        file_edits.sort(key=lambda e: e["line"], reverse=True)

        for edit in file_edits:
            line_idx = edit["line"] - 1
            original = edit["original"]
            replacement = edit["replacement"]

            if original == replacement:
                skipped += 1
                continue

            if line_idx < 0 or line_idx >= len(lines):
                errors.append(
                    f"{rel_path}:{edit['line']} — line out of range"
                )
                skipped += 1
                continue

            line = lines[line_idx]
            if original not in line:
                # Try adjacent lines (parser position can be off by 1)
                found = False
                for offset in ADJACENT_LINE_OFFSETS:
                    adj = line_idx + offset
                    if 0 <= adj < len(lines) and original in lines[adj]:
                        lines[adj] = lines[adj].replace(original, replacement, 1)
                        applied += 1
                        found = True
                        break
                if not found:
                    errors.append(
                        f"{rel_path}:{edit['line']} — original text not found "
                        f"on line: {original!r:.60}"
                    )
                    skipped += 1
            else:
                lines[line_idx] = line.replace(original, replacement, 1)
                applied += 1

        with open(abs_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    return {"applied": applied, "skipped": skipped, "errors": errors}
