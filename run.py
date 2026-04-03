import json
import os
import random
import re
import zipfile
import shutil

import py7zr
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

from vimm_types import VimmMedia

USER_AGENTS: list[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
]

# Used for renaming/deleting the .txt file that comes with each download
vimm_txt_filename = "Vimm's Lair.txt"

SETTINGS = {}
if os.path.exists("settings.json"):
    with open("settings.json", "r") as f:
        SETTINGS = json.load(f)

script_name = os.path.basename(__file__)
ROOT_DIRECTORY = os.path.abspath(__file__)
# Slice off the 'run.py' portion of the path, plus a trailing slash
ROOT_DIRECTORY = ROOT_DIRECTORY[0: -(len(script_name) + 1)]

DEFAULT_ROOT_DOWNLOAD_DIRECTORY = os.path.join(ROOT_DIRECTORY, "downloading")
DEFAULT_ROOT_FINISHED_DIRECTORY = os.path.join(ROOT_DIRECTORY, "finished")
ROOT_FINISHED_DIRECTORY = DEFAULT_ROOT_FINISHED_DIRECTORY
if "rootFinishedDirectory" in SETTINGS and SETTINGS["rootFinishedDirectory"] != "":
    ROOT_FINISHED_DIRECTORY = SETTINGS["rootFinishedDirectory"]

SOURCE_DIRECTORY = os.path.join(ROOT_DIRECTORY, "consoles")
DOWNLOAD_HISTORY_DIRECTORY = os.path.join(ROOT_DIRECTORY, "history")


def get_random_ua() -> str:
    """Returns a random user agent for download method"""
    index: int = random.randint(0, len(USER_AGENTS) - 1)
    return USER_AGENTS[index]


def get_media(url: str) -> VimmMedia | None:
    print(f"Getting media information from {url}")
    response = requests.get(url, verify=False)

    # Exit early if status code indicates any error
    if response.status_code != 200:
        print("Error getting media:", response.status_code)
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    media_id_element = soup.find("input", {"name": "mediaId"})
    url_element = soup.find("form", {"id": "dl_form"})

    if not media_id_element:
        print("Unable to find media")
        return None

    if not url_element:
        print("Unable to find download url")
        return None

    media_id = str(media_id_element["value"])
    if not media_id.isdigit():
        print(f"Media id invalid: {media_id}(is {type(media_id)}")
        return None

    download_history = get_history()
    if media_id in download_history:
        print(f"WARNING: {url} has been downloaded previously.")
        print(
            f"WARNING: Remove {media_id} from {
                DOWNLOAD_HISTORY_DIRECTORY
            }/download_history.csv to download it again."
        )
        add_to_failed_downloads(url)
        return None
    media_id = int(media_id)

    download_url = url_element["action"]
    if not isinstance(download_url, str):
        print(f"Download url is invalid: {download_url}")
        return None

    # Check download_url matches what an action url looks like
    # E.g.: //dl3.vimm.net/ or //dl2.vimm.net/
    download_url_pattern = re.compile(r"^\/\/dl\d?\.vimm\.net\/$")
    if not download_url_pattern.match(download_url):
        print(f"Download url is invalid: {download_url}")
        print("Example download url: //dl3.vimm.net/[MEDIA_ID]")
        return None

    # Everything looks good
    return {"id": media_id, "url": download_url}


def download(media: VimmMedia, destination: str):
    archive_path = None
    downloadUrl = f"https:{media['url']}?mediaId={media['id']}"
    print(downloadUrl)
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        "Connection": "keep-alive",
        "Cookie": "__qca=I0-1342370008-1747309780452; _ga=GA1.1.1175809765.1747138134; AWSUSER_ID=awsuser_id1747138134137r3241; usprivacy=1N--; _sharedID=198ad7f1-fc13-4031-94d5-b6248fb04e22; _lr_env_src_ats=false; _cc_id=f56dab5fa81316ab7f8c5abe46e1505b; panoramaId_expiry=1747742924246; panoramaId=ba332d2f58c66aeb74f3c16a4ef94945a702ee765cb2aaf02c55a93ee0b84699; panoramaIdType=panoIndiv; _pbjs_userid_consent_data=3524755945110770; pbjs-unifiedid=%7B%22TDID%22%3A%2284398995-efdb-40ef-ae45-9de85e5e000b%22%2C%22TDID_LOOKUP%22%3A%22FALSE%22%2C%22TDID_CREATED_AT%22%3A%222025-05-14T11%3A25%3A57%22%7D; pbjs-unifiedid_cst=VyxHLMwsHQ%3D%3D; pbjs-unifiedid_last=Wed%2C%2014%20May%202025%2011%3A26%3A00%20GMT; FCNEC=%5B%5B%22AKsRol8DsZXR94uXRzLKroxC1CUagbaD_GhBXRlrDd5HLvdAkv_aYvAG-36Of4VhLMCFdJOpCKrI7L0jIHT70w9mZc-cQNSWxGTlVfla-rD9aEQEi2foimmzRCqDm0x2luPk5Q3rkPQ30LITKlhNqsLOvVLrJZog8g%3D%3D%22%5D%5D; _sharedID=198ad7f1-fc13-4031-94d5-b6248fb04e22; _sharedID_cst=kSylLAssaw%3D%3D; _sharedID_last=Wed%2C%2014%20May%202025%2019%3A03%3A14%20GMT; _ga_4BESX0QC2N=deleted; counted=1; PHPSESSID=m35imrfpejp9c8psd194r5fho8; AWSSESSION_ID=awssession_id1747309696995r3939; _ga_4BESX0QC2N=GS2.1.s1747309697$o11$g0$t1747309697$j0$l0$h0; _awl=2.1747309694.5-667ce87a3ddf36164610146f28534810-6763652d75732d6561737431-0; _sharedID_cst=kSylLAssaw%3D%3D; cto_bidid=rUpChV9PNlRhTU9PUWxXSCUyRkthcUF2YXVjQTRUQyUyQld1eE1qWVBoJTJGY1NZakp6MUh2TUYxcVVzaWIyN08ySFN4d3Z3MlJRdXlzWnpNMmlvRFNHb3hZU0ZJS2dGc29FVnp2VnFlMTJhV0NVQmlTV0R3NCUzRA; cto_dna_bundle=luzugV9RVGdDQ0ZKak9sUEtQM1RpVzdVdFA0dmJtQUdYVWwlMkZyWW1jZmlTWUdOZ3JPd21PSnRrR3hnNWhrWDRwYjUwaTBZVWxyWjVVNjlaT2k3bTBDaE1rTVNBJTNEJTNE; cto_bundle=nbAY6F9RVGdDQ0ZKak9sUEtQM1RpVzdVdFA2UVJNWENkWE5Qc3g1cGtoNUE1JTJCY2NpSlUyMzJkNUdLJTJCeTdsMEtMVFElMkJJNnh1QXlUUE9XN0huMXFtODJzeGt0eCUyQk5xd0phU2xZaDJrNm1XMm4lMkZLU0kzcFEzcyUyQjhyRzJPelVqUnRXWW02VXpOaFBRRngzNlJvVWxnbXJQd1V4aEElM0QlM0Q; __gads=ID=c82e2ea87bee2953:T=1747138125:RT=1747311707:S=ALNI_MaH5U2VXdlREnRpIqJsVCM9JyW6cA; __eoi=ID=241794a8d0acedda:T=1747138125:RT=1747311707:S=AA-AfjZvrpIAAE8ZfDsr6IZCeEtZ",
        "Host": media["url"].replace("/", ""),
        "Referer": "https://vimm.net/vault/8415",
        "Sec-Ch-Ua": '"Chromium";v="136", "Microsoft Edge";v="136", "Not.A/Brand";v="99"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-site",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": get_random_ua(),
    }
    with requests.get(
        downloadUrl, headers=headers, stream=True, verify=False
    ) as response:
        if response.status_code == 200 or response.status_code == 304:
            total_size = int(response.headers.get("content-length", 0))
            content_disposition = response.headers.get("content-disposition")
            filename = None
            match = re.search(r'filename="(.+?)"', content_disposition)
            if match:
                filename = match.group(1)
            archive_path = os.path.join(
                DEFAULT_ROOT_DOWNLOAD_DIRECTORY, filename)
            os.makedirs(os.path.dirname(archive_path), exist_ok=True)
            with tqdm(
                total=total_size, unit="B", unit_scale=True, desc=archive_path
            ) as pbar:
                with open(archive_path, "wb") as file:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            file.write(chunk)
                            pbar.update(len(chunk))
            print("Download finished!")
            return archive_path
        else:
            print("Error downloading media:",
                  response.text, response.status_code)
            return archive_path


def extract_and_delete(archive_path: str, extract_dir: str) -> bool:
    try:
        ensure_directory_exists(extract_dir)
        print(f"Extracting {archive_path}")
        archive_directory, media_title = os.path.split(archive_path)
        # Remove extension from file name
        media_title = media_title.rsplit(".", 1)[0]
        if archive_path.endswith(".zip"):
            with zipfile.ZipFile(archive_path, "r") as zip_ref:
                zip_ref.extractall(archive_directory)
                print(f"Extracted zip: {archive_path} to {archive_directory}")
        elif archive_path.endswith(".7z"):
            with py7zr.SevenZipFile(archive_path, "r") as seven_zip:
                seven_zip.extractall(archive_directory)
                print(f"Extracted 7z: {archive_path} to {archive_directory}")
        else:
            print(f"Unsupported file format: {archive_path}")
            return False
        # Delete downloaded archive
        os.remove(archive_path)
        # Delete or rename included Vimm.txt file to match downloaded media title
        for file in os.listdir(archive_directory):
            file_path = os.path.join(archive_directory, file)
            if file == vimm_txt_filename:
                if "removeVimmTxt" in SETTINGS and SETTINGS["removeVimmTxt"]:
                    print(f"Deleting {vimm_txt_filename}")
                    os.remove(file_path)
                else:
                    print(f"Renaming {vimm_txt_filename}")
                    media_title_txt = os.path.join(
                        archive_directory, f"{media_title}.txt"
                    )
                    os.rename(file_path, media_title_txt)
                break
        # Optionally re-zip files for storage
        if "rezip" in SETTINGS and SETTINGS["rezip"]:
            print("compressing downloaded files...")
            new_zip = os.path.join(extract_dir, media_title)
            shutil.make_archive(new_zip, "zip", archive_directory)
            for file in os.listdir(archive_directory):
                if file.endswith(".zip"):
                    continue
                print(f"removing file {file}")
                os.remove(os.path.join(archive_directory, file))
            return True
        # Move everything where it belongs
        for file in os.listdir(archive_directory):
            file_path = os.path.join(archive_directory, file)
            destination_path = os.path.join(extract_dir, file)
            os.rename(file_path, destination_path)
        return True
    except Exception as e:
        print(f"Error extracting {archive_path}: {e}")
        return False


def download_from_txt(file: str, destination: str):
    vimm_vault_pattern = re.compile(r"^https?:\/\/vimm\.net\/vault\/.+$")
    with open(file, "r") as f:
        lines = f.readlines()
        for line in lines:
            url = line.strip()
            if not vimm_vault_pattern.match(url):
                print(f"{url} is not a valid vimm vault url. Skipping...")
                continue
            print(f"URL: {url}")
            media = get_media(url)
            if media is None:
                print("Media not found")
                continue
            print(f"Media found: {media['id']} {media['url']}")
            archive_path = download(media, destination)
            # Download failed
            if archive_path is None:
                add_to_failed_downloads(media["url"])
                continue
            # Download succeeded
            add_to_history(media["id"])
            if extract_and_delete(archive_path, destination):
                print(f"Successfully extracted and deleted {archive_path}")
            else:
                print(f"Failed to extract or delete {archive_path}")


def add_to_history(id: int):
    ensure_directory_exists(DOWNLOAD_HISTORY_DIRECTORY)
    history_file = os.path.join(
        DOWNLOAD_HISTORY_DIRECTORY, "download_history.csv")
    if not os.path.exists(history_file):
        with open(history_file, "x") as f:
            f.write(f"{id}")
        return
    with open(history_file, "a") as f:
        f.write(f",{id}")


def add_to_failed_downloads(url: str):
    ensure_directory_exists(DOWNLOAD_HISTORY_DIRECTORY)
    failed_downloads = os.path.join(
        DOWNLOAD_HISTORY_DIRECTORY, "failed_downloads.csv")
    if not os.path.exists(failed_downloads):
        with open(failed_downloads, "x") as f:
            f.write(f"{url}")
        return
    with open(failed_downloads, "a") as f:
        f.write(f",{url}")


def get_history() -> str:
    ensure_directory_exists(DOWNLOAD_HISTORY_DIRECTORY)
    history_file = os.path.join(
        DOWNLOAD_HISTORY_DIRECTORY, "download_history.csv")
    if not os.path.exists(history_file):
        return ""
    with open(history_file, "r") as f:
        return f.readline()


def get_consoles() -> list[str]:
    consoles = []
    for file in os.listdir(SOURCE_DIRECTORY):
        if file.endswith(".txt"):
            consoles.append(file)
    return consoles


def ensure_directory_exists(directory: str):
    if not os.path.isdir(directory):
        print(f"Creating directory at {directory}")
        try:
            os.makedirs(directory)
        except Exception as e:
            print(f"Error creating directory at {directory}")
            print("Error:", e)
            raise e


def ensure_base_dirs_exist():
    base_dirs = [
        SOURCE_DIRECTORY,
        DEFAULT_ROOT_FINISHED_DIRECTORY,
        DEFAULT_ROOT_DOWNLOAD_DIRECTORY,
    ]
    for dir in base_dirs:
        ensure_directory_exists(dir)


def main():
    ensure_base_dirs_exist()
    consoles = get_consoles()

    for console_txt in consoles:
        print(f"Downloading from {console_txt}")
        console_name = console_txt[:-4]
        path_to_console = os.path.join(SOURCE_DIRECTORY, console_txt)
        destination = os.path.join(ROOT_FINISHED_DIRECTORY, console_name)
        if console_txt in SETTINGS and SETTINGS[console_txt] != "":
            destination = SETTINGS[console_txt]
        elif console_name in SETTINGS and SETTINGS[console_name] != "":
            destination = SETTINGS[console_name]
        ensure_directory_exists(destination)
        download_from_txt(path_to_console, destination)
    print("Finished downloading!")
    print(
        f"Check {
            DOWNLOAD_HISTORY_DIRECTORY
        }/failed_downloads.csv to view any potentially failed download links."
    )


if __name__ == "__main__":
    main()
