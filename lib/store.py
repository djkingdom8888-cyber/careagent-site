import json
import os
import tempfile
import threading

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# On Render this is set to the mounted persistent disk (e.g. /data) so content,
# the admin account, and the secret key all survive redeploys. Locally it just
# falls back to this project's own data/ folder.
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(BASE_DIR, "data"))
os.makedirs(DATA_DIR, exist_ok=True)
CONTENT_PATH = os.path.join(DATA_DIR, "content.json")
ADMIN_PATH = os.path.join(DATA_DIR, "admin.json")
_SEED_CONTENT_PATH = os.path.join(BASE_DIR, "data", "content.json")


def _ensure_content_seeded():
    """First boot against an empty persistent disk: seed it from the repo's
    checked-in content.json so the site isn't blank until someone edits it."""
    if not os.path.exists(CONTENT_PATH) and os.path.exists(_SEED_CONTENT_PATH):
        with open(_SEED_CONTENT_PATH, "r") as f:
            seed = f.read()
        with open(CONTENT_PATH, "w") as f:
            f.write(seed)


_ensure_content_seeded()

_lock = threading.Lock()


def _atomic_write(path, data):
    directory = os.path.dirname(path)
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def load_content():
    with _lock:
        with open(CONTENT_PATH, "r") as f:
            return json.load(f)


def save_content(data):
    with _lock:
        _atomic_write(CONTENT_PATH, data)


def load_admin():
    with _lock:
        with open(ADMIN_PATH, "r") as f:
            return json.load(f)


def save_admin(data):
    with _lock:
        _atomic_write(ADMIN_PATH, data)


def get_path(data, path):
    node = data
    for key in path:
        node = node[key]
    return node


def set_path(data, path, value):
    node = data
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
