"""
Entry point for running the Text Manager as a module.

Usage (from the gooey/ directory):
    python -m text_manager
    python -m text_manager --port 5001

Or from the repo root:
    python -m gooey.text_manager
"""

import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser(
        description="annieData Text Manager — edit all user-facing text in one place"
    )
    parser.add_argument(
        "--port", type=int, default=5001,
        help="Port to run the web UI on (default: 5001)"
    )
    parser.add_argument(
        "--gooey-dir", type=str, default=None,
        help="Path to the gooey/ directory (auto-detected if omitted)"
    )
    parser.add_argument(
        "--no-debug", action="store_true",
        help="Disable Flask debug mode"
    )
    args = parser.parse_args()

    # Auto-detect gooey dir
    if args.gooey_dir:
        gooey_dir = os.path.abspath(args.gooey_dir)
    else:
        # Try relative to this file, then relative to cwd
        this_dir = os.path.dirname(os.path.abspath(__file__))
        if os.path.basename(this_dir) == "text_manager":
            gooey_dir = os.path.dirname(this_dir)
        elif os.path.isdir(os.path.join(os.getcwd(), "app")):
            gooey_dir = os.getcwd()
        else:
            # Try parent of cwd
            parent = os.path.dirname(os.getcwd())
            if os.path.isdir(os.path.join(parent, "gooey", "app")):
                gooey_dir = os.path.join(parent, "gooey")
            else:
                print("Error: Could not find gooey/ directory.")
                print("Run from the gooey/ directory or pass --gooey-dir")
                sys.exit(1)

    # Verify the gooey dir has the expected structure
    index_html = os.path.join(gooey_dir, "app", "templates", "index.html")
    if not os.path.isfile(index_html):
        print(f"Error: {index_html} not found.")
        print("Make sure --gooey-dir points to the gooey/ directory.")
        sys.exit(1)

    from .server import run
    run(gooey_dir, port=args.port, debug=not args.no_debug)


if __name__ == "__main__":
    main()
