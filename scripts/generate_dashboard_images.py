#!/usr/bin/env python3
"""Entry point — renders premium HTML dashboards to PNG."""

import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    script = Path(__file__).resolve().parent / "render_dashboard_html.py"
    sys.exit(subprocess.call([sys.executable, str(script)]))
