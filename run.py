import os
import re

from config import DOWNLOAD_DIR, SOURCE_DIR, FINISHED_DIR, SETTINGS
from downloader import get_media, download
from extractor import extract_and_delete
from history import add_to_history, add_to_failed_downloads


def main():
    _ensure_base_dirs()

    for console_txt in os.listdir(SOURCE_DIR):
        if not console_txt.endswith(".txt"):
            continue

        print(f"Downloading from {console_txt}")
        console_name = console_txt[:-4]
        source_path = os.path.join(SOURCE_DIR, console_txt)
        destination = _get_destination(console_txt, console_name)
        os.makedirs(destination, exist_ok=True)
        _process_console_file(source_path, destination)

    print("Finished downloading!")
    print("Check history/failed_downloads.csv for any failed downloads.")


def _process_console_file(file_path: str, destination: str):
    vimm_pattern = re.compile(r"^https?:\/\/vimm\.net\/vault\/.+$")

    with open(file_path, "r") as f:
        for line in f:
            parts = line.strip().split()
            if not parts:
                continue

            url = parts[0]
            if not vimm_pattern.match(url):
                print(f"{url} is not a valid vimm vault url. Skipping...")
                continue

            alt = _parse_optional_int(parts, 1)
            version = _parse_optional_int(parts, 2)

            print(f"URL: {url}, alt: {alt}, version: {version}")
            media = get_media(url, alt, version)
            if not media:
                print("Media not found")
                continue

            print(f"Media found: {media['id']} {media['url']}")
            archive_path = download(media)

            if not archive_path:
                add_to_failed_downloads(media["url"])
                continue

            add_to_history(media["id"])
            if extract_and_delete(archive_path, destination):
                print(f"Successfully extracted {archive_path}")
            else:
                print(f"Failed to extract {archive_path}")


def _parse_optional_int(parts: list, index: int) -> int | None:
    if index >= len(parts) or parts[index] == "":
        return None
    try:
        return int(parts[index])
    except ValueError:
        print(f"Argument at position {index} is not a number. Skipping.")
        add_to_failed_downloads(parts[0])
        return None


def _get_destination(console_txt: str, console_name: str) -> str:
    if SETTINGS.get(console_txt):
        return SETTINGS[console_txt]
    if SETTINGS.get(console_name):
        return SETTINGS[console_name]
    return os.path.join(FINISHED_DIR, console_name)


def _ensure_base_dirs():
    os.makedirs(SOURCE_DIR, exist_ok=True)
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    os.makedirs(FINISHED_DIR, exist_ok=True)


if __name__ == "__main__":
    main()
