"""Download Supreme Court of India judgments (English PDFs in one tar per year) + parquet metadata from the public
AWS Open Data bucket (CC-BY-4.0, curated by Dattam Labs from the eCourts website).
Usage:  python scripts/fetch_data.py 2018 2019 2020 2021 2022 2023 2024
Each year is ~200-430 MB.  Resumes a partial download.  No AWS account needed."""
import sys
import urllib.request
from pathlib import Path

BASE = "https://indian-supreme-court-judgments.s3.ap-south-1.amazonaws.com"
ROOT = Path(__file__).resolve().parent.parent


def fetch(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    have = dest.stat().st_size if dest.exists() else 0
    req = urllib.request.Request(url, headers={"Range": f"bytes={have}-"} if have else {})
    try:
        with urllib.request.urlopen(req) as r, open(dest, "ab" if have else "wb") as f:
            while chunk := r.read(1 << 20):
                f.write(chunk)
    except urllib.error.HTTPError as e:
        if e.code != 416:  # 416 = already complete
            raise


if __name__ == "__main__":
    for y in sys.argv[1:] or ["2018", "2019", "2020", "2021", "2022", "2023", "2024"]:
        print("year", y, flush=True)
        fetch(f"{BASE}/metadata/parquet/year={y}/metadata.parquet", ROOT / "data" / "meta" / f"{y}.parquet")
        fetch(f"{BASE}/data/tar/year={y}/english/english.tar", ROOT / "data" / "tar" / f"{y}.tar")
