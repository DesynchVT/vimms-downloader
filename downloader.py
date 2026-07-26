import os
import random
import re
import requests
from bs4 import BeautifulSoup

from config import USER_AGENTS, HISTORY_DIR, SETTINGS, DOWNLOAD_DIR, FINISHED_DIR
from vimm_types import VimmMedia


def get_random_ua() -> str:
    return random.choice(USER_AGENTS)


def get_media(
    url: str, alt: int | None = None, version: int | None = None
) -> VimmMedia | None:

    print(f"Getting media information from {url}")
    response = requests.get(url, verify=False)

    if response.status_code != 200:
        print("Error getting media:", response.status_code)
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    media_id_element = soup.find("input", {"name": "mediaId"})
    url_element = soup.find("form", {"id": "dl_form"})

    if not media_id_element or not url_element:
        print("Unable to find media or download url")
        return None

    media_id = str(media_id_element["value"])
    if not media_id.isdigit():
        print(f"Media id invalid: {media_id}")
        return None

    from history import get_history, add_to_failed_downloads

    if media_id in get_history():
        print(f"WARNING: {url} has been downloaded previously.")
        print(
            f"WARNING: Remove {media_id} from {HISTORY_DIR}/download_history.csv to download it again."
        )
        add_to_failed_downloads(url)
        return None

    media_id = int(media_id)
    download_url = url_element["action"]

    if alt:
        format_elements = soup.find("select", {"id": "dl_format"})
        if not format_elements:
            print("Could not find alternate formats. Skipping.")
            add_to_failed_downloads(url)
            return None

        alt_options = format_elements.find_all("option")
        if not any(opt["value"] == str(alt) for opt in alt_options):
            print(f"Could not find a format with value {alt}. Skipping.")
            add_to_failed_downloads(url)
            return None

    download_url_pattern = re.compile(r"^\/\/dl\d?\.vimm\.net\/$")
    if not download_url_pattern.match(download_url):
        print(f"Download url is invalid: {download_url}")
        return None

    return {"id": media_id, "url": download_url, "alt": alt, "version": version}


def download(media: VimmMedia) -> str | None:
    import re
    import requests
    from tqdm import tqdm

    download_url = f"https:{media['url']}?mediaId={media['id']}"
    if media["alt"]:
        download_url += f"&alt={media['alt']}"
    print(download_url)

    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        "Connection": "keep-alive",
        "Cookie": "__qca=I0-1342370008-1747309780452; _ga=GA1.1.1175809765.1747138134; AWSUSER_ID=awsuser_id1747138134137r3241; usprivacy=1N--; _sharedID=198ad7f1-fc13-4031-94d5-b6248fb04e22; _lr_env_src_ats=false; _cc_id=f56dab5fa81316ab7f8c5abe46e1505b; panoramaId_expiry=1747742924246; panoramaId=ba332d2f58c66aeb74f3c16a4ef94945a702ee765cb2aaf02c55a93ee0b84699; panoramaIdType=panoIndiv; _pbjs_userid_consent_data=3524755945110770; pbjs-unifiedid=%7B%22TDID%22%3A%2284398995-efdb-40ef-ae45-9de85e5e000b%22%2C%22TDID_LOOKUP%22%3A%22FALSE%22%2C%22TDID_CREATED_AT%22%3A%222025-05-14T11%3A25%3A57%22%7D; pbjs-unifiedid_cst=VyxHLMwsHQ%3D%3D; pbjs-unifiedid_last=Wed%2C%2014%20May%202025%2011%3A26%3A00%20GMT; FCNEC=%5B%5B%22AKsRol8DsZXR94uXRzLKroxC1CUagbaD_GhBXRlrDd5HLvdAkv_aYvAG-36Of4VhLMCFdJOpCKrI7L0jIHT70w9mZc-cQNSWxGTlVfla-rD9aEQEi2foimmzRCqDm0x2luPk5Q3rkPQ30LITKlhNqsLOvVLrJZog8g%3D%3D%22%5D%5D; _sharedID=198ad7f1-fc13-4031-94d5-b6248fb04e22; _sharedID_cst=kSylLAssaw%3D%3D; _sharedID_last=Wed%2C%2014%20May%202025%2019%3A03%3A14%20GMT; _ga_4BESX0QC2N=deleted; counted=1; PHPSESSID=m35imrfpejp9c8psd194r5fho8; AWSSESSION_ID=awssession_id1747309696995r3939; _ga_4BESX0QC2N=GS2.1.s1747309697$o11$g0$t1747309697$j0$l0$h0; _awl=2.1747309694.5-667ce87a3ddf36164610146f28534810-6763652d75732d6561737431-0; _sharedID_cst=kSylLAssaw%3D%3D; cto_bidid=rUpChV9PNlRhTU9PUWxXSCUyRkthcUF2YXVjQTRUQyUyQld1eE1qWVBoJTJGY1NZakp6MUh2TUYxcVVzaWIyN08ySFN4d3Z3MlJRdXlzWnpNMmlvRFNHb3hZU0ZJS2dGc29FVnp2VnFlMTJhV0NVQmlTV0R3NCUzRA; cto_dna_bundle=luzugV9RVGdDQ0ZKak9sUEtQM1RpVzdVdFA0dmJtQUdYVWwlMkZyWW1jZmlTWUdOZ3JPd21PSnRrR3hnNWhrWDRwYjUwaTBZVWxyWjVVNjlaT2k3bTBDaE1rTVNBJTNEJTNE; cto_bundle=nbAY6F9RVGdDQ0ZKak9sUEtQM1RpVzdVdFA2UVJNWENkWE5Qc3g1cGtoNUE1JTJCY2NpSlUyMzJkNUdLJTJCeTdsMEtMVFElMkJJNnh1QXlUUE9XN0huMXFtODJzeGt0eCUyQk5xd0phU2xZaDJrNm1XMm4lMkZLU0kzcFEzcyUyQjhyRzJPelVqUnRXWW02VXpOaFBRRngzNlJvVWxnbXJQd1V4aEElM0QlM0Q; __gads=ID=c82e2ea87bee2953:T=1747138125:RT=1747311707:S=ALNI_MaH5U2VXdlREnRpIqJsVCM9JyW6cA",
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
        download_url, headers=headers, stream=True, verify=False
    ) as response:
        if response.status_code not in (200, 304):
            print("Error downloading media:", response.text, response.status_code)
            return None

        total_size = int(response.headers.get("content-length", 0))
        content_disposition = response.headers.get("content-disposition")
        filename = ""
        match = re.search(r'filename="(.+?)"', content_disposition or "")
        if match:
            filename = match.group(1)

        archive_path = os.path.join(DOWNLOAD_DIR, filename)
        os.makedirs(os.path.dirname(archive_path), exist_ok=True)

        with tqdm(
            total=total_size, unit="B", unit_scale=True, desc=archive_path
        ) as pbar:
            with open(archive_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))

        print("Download finished!")
        return archive_path
