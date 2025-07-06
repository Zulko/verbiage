import requests
from pathlib import Path


def download(url, filename, replace=False):
    """Download the file (check if it already exists)"""
    if Path(filename).exists() and not replace:
        print(f"File {filename} already exists")
        return
    print(f"Downloading {url} to {filename}")
    response = requests.get(url)
    with open(filename, "wb") as f:
        f.write(response.content)
