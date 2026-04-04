from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parent
SRC_DIR = PACKAGE_DIR.parent
PROJECT_ROOT = SRC_DIR.parent

ASSETS_DIR = PROJECT_ROOT / "assets"
BIN_DIR = ASSETS_DIR / "bin"
FONTS_DIR = ASSETS_DIR / "fonts"
IMAGES_DIR = ASSETS_DIR / "images"

EXAMPLES_DIR = PROJECT_ROOT / "examples"
WORKSPACE_DIR = PROJECT_ROOT / "workspace"
UPLOADS_DIR = WORKSPACE_DIR / "uploads"
API_CASES_DIR = WORKSPACE_DIR / "api_cases"
REPORTS_DIR = WORKSPACE_DIR / "reports"

