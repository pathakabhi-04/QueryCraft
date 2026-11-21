import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "data"))

from querycraft.config import DB_PATH  # noqa: E402

if not DB_PATH.exists():
    import generate_db  # noqa: E402
    generate_db.build(DB_PATH)
