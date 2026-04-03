# Vimm's Lair Downloader

## Description

This is a simple script to download all the files you want from Vimm's Lair. It uses the `requests` library to make HTTP requests and `BeautifulSoup` to parse HTML. The script downloads all the files from the specified page and saves them to a local directory. It also extracts them to a specified directory to avoid duplicates. The script prevents downloading previously downloaded files by keeping a download history in a CSV file.

## Requirements

- Python 3.x

## Usage

Clone the repository and install the required packages:

```bash
git clone REPOSITORY_URL_HERE
cd vimms-downloader
pip install -r requirements.txt
```

Create a folder named `consoles` in the same directory as the script. Inside the `console` folder, create a text file with whatever name you want such as `PS2.txt`. Text files inside the `consoles` folder should contain the URLs of the pages you want to download from, one per line. For example:

```text (PS2.txt)
https://vimm.net/vault/7836
https://vimm.net/vault/7970
https://vimm.net/vault/8000
```

You can create as many text files inside `consoles` as you want. Downloaded files will automatically be sorted into a subdirectory of the same name in the `finished` directory. For example, `finished/PS2/Bully (USA).iso` from `consoles/PS2.txt`.
You can of course also just dump every link into a single file called `links.txt` or something, if you want.

The script will automatically create three directories if they do not exist:
`downloading` to store temp files.
`finished` to store fully downloaded files.
`history` to store download history and errors. This is to avoid repeated downloads of the same file.

Then, run the script:

```bash
python3 run.py
```

That's it! The script will download all the files from the specified pages in every .txt file in the "consoles" folder and save them to "downloading" folder, then extract to "finished" folder and delete the compressed file.

## Customization

Everything mentioned above is the default behaviour. You can easily change parts of the process by editing the `settings.json` file.
Deleting any of the keys `rootFinishedDirectory`, `rezip`, and `removeVimmTxt` will result in the script assuming its default behaviour.

```json
{
  // Absolute path to storing downloaded files.
  // Still sorts downloads into subdirectories, but at your specified location instead.
  "rootFinishedDirectory": "",
  // Change to true to zip downloaded files after download.
  // For smaller file size, and making sure all downloads are the .zip format.
  "rezip": false,
  // Change to true to delete the "Vimm's Lair.txt" file included in every download.
  // Default behaviour is to rename it to the downloaded file's title.
  "removeVimmTxt": false
}
```

You can also store each system's files in a completely different location by adding your .txt file from `consoles` to `settings.json`. If we take our `PS2.txt` example from above, it could look like this

```jsonc
{
  // Example file paths are Linux-style.
  // Use two backslashes on windows instead.
  // Or just copy the path from your file explorer.
  "rootFinishedDirectory": "/path/to/my/collection",
  "rezip": false,
  "removeVimmTxt": false,
  "PS2": "/some/other/path", // <- Downloads from PS2.txt will be store here instead of the path above
}
```
