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
FEEDBACK_DIR = WORKSPACE_DIR / "feedback"
FEEDBACK_DB_PATH = FEEDBACK_DIR / "feedback.sqlite3"


def ensure_directories() -> None:
    """集中创建所有运行时目录，避免各模块分散 mkdir 导致干净部署时写文件失败。"""
    for directory in (
        ASSETS_DIR,
        BIN_DIR,
        FONTS_DIR,
        IMAGES_DIR,
        EXAMPLES_DIR,
        WORKSPACE_DIR,
        UPLOADS_DIR,
        API_CASES_DIR,
        REPORTS_DIR,
        FEEDBACK_DIR,
    ):
        directory.mkdir(parents=True, exist_ok=True)


# 任何模块导入 paths 时即完成目录初始化，保证常量指向的父目录始终存在。
ensure_directories()
