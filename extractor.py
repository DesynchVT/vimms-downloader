import os
import shutil
import subprocess
import tarfile
import zipfile

import py7zr

from config import SETTINGS, VIMM_TXT_FILENAME


def extract_and_delete(archive_path: str, extract_dir: str) -> bool:
    try:
        os.makedirs(extract_dir, exist_ok=True)
        print(f"Extracting {archive_path}")

        archive_dir, media_title = os.path.split(archive_path)
        media_title = media_title.rsplit(".", 1)[0]

        if archive_path.endswith(".zip"):
            with zipfile.ZipFile(archive_path, "r") as zip_ref:
                zip_ref.extractall(archive_dir)
        elif archive_path.endswith(".7z"):
            with py7zr.SevenZipFile(archive_path, "r") as seven_zip:
                seven_zip.extractall(archive_dir)
        else:
            print(f"Unsupported file format: {archive_path}")
            return False

        os.remove(archive_path)
        _handle_vimm_txt(archive_dir, media_title)

        if SETTINGS.get("rezip"):
            _recompress_contents(archive_dir, extract_dir, media_title)
        else:
            _move_contents(archive_dir, extract_dir)

        return True
    except Exception as e:
        print(f"Error extracting {archive_path}: {e}")
        return False


def _handle_vimm_txt(archive_dir: str, media_title: str):
    vimm_txt_path = os.path.join(archive_dir, VIMM_TXT_FILENAME)
    if not os.path.exists(vimm_txt_path):
        return

    if SETTINGS.get("removeVimmTxt"):
        print(f"Deleting {VIMM_TXT_FILENAME}")
        os.remove(vimm_txt_path)
    else:
        print(f"Renaming {VIMM_TXT_FILENAME}")
        new_path = os.path.join(archive_dir, f"{media_title}.txt")
        os.rename(vimm_txt_path, new_path)


def _recompress_contents(archive_dir: str, extract_dir: str, media_title: str):
    print("Compressing downloaded files...")
    out_path = os.path.join(extract_dir, f"{media_title}.tar.xz")
    os.makedirs(extract_dir, exist_ok=True)
    try:
        with open(out_path, "wb") as out_file:
            xz_proc = subprocess.Popen(
                ["xz", "-T0", "-9", "-c"],
                stdin=subprocess.PIPE,
                stdout=out_file,
            )
            with tarfile.open(
                fileobj=xz_proc.stdin, mode="w|", format=tarfile.PAX_FORMAT
            ) as tar:
                tar.add(archive_dir, arcname=".")
            xz_proc.stdin.close()
            if xz_proc.wait() != 0:
                raise RuntimeError(f"xz compression failed: {out_path}")

        if subprocess.run(["xz", "-t", out_path]).returncode != 0:
            raise RuntimeError(f"xz integrity check failed: {out_path}")
    except Exception:
        if os.path.exists(out_path):
            os.remove(out_path)
        raise

    for file in os.listdir(archive_dir):
        file_path = os.path.join(archive_dir, file)
        print(f"Removing {file}")
        if os.path.isdir(file_path):
            shutil.rmtree(file_path)
        else:
            os.remove(file_path)


def _move_contents(archive_dir: str, extract_dir: str):
    for file in os.listdir(archive_dir):
        src = os.path.join(archive_dir, file)
        dst = os.path.join(extract_dir, file)
        os.rename(src, dst)
