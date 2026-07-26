"""Set the bundled Playwright browser path before application imports."""
from __future__ import annotations

import os
import sys
from pathlib import Path


if getattr(sys, 'frozen', False):
    bundle_root = Path(getattr(sys, '_MEIPASS'))
    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(
        bundle_root / 'ms-playwright'
    )
