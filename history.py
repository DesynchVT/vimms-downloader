import os

from config import HISTORY_DIR


def add_to_history(media_id: int):
    _ensure_dir()
    history_file = os.path.join(HISTORY_DIR, "download_history.csv")

    if not os.path.exists(history_file):
        with open(history_file, "x") as f:
            f.write(str(media_id))
    else:
        with open(history_file, "a") as f:
            f.write(f",{media_id}")


def add_to_failed_downloads(url: str):
    _ensure_dir()
    failed_file = os.path.join(HISTORY_DIR, "failed_downloads.csv")

    if not os.path.exists(failed_file):
        with open(failed_file, "x") as f:
            f.write(url)
    else:
        with open(failed_file, "a") as f:
            f.write(f",{url}")


def get_history() -> str:
    _ensure_dir()
    history_file = os.path.join(HISTORY_DIR, "download_history.csv")

    if not os.path.exists(history_file):
        return ""
    with open(history_file, "r") as f:
        return f.readline()


def _ensure_dir():
    os.makedirs(HISTORY_DIR, exist_ok=True)
