import csv
import io
import shutil
import zipfile
from pathlib import Path

import httpx

from app.trains.feeds import FEEDS, Feed

# Downloaded feeds live here, one folder per feed. Git-ignored.
GTFS_DIR = Path(__file__).resolve().parents[2] / "data" / "gtfs"


def unpack(zip_bytes: bytes, folder: Path) -> list[str]:
    """Replace the folder's contents with the zip's .txt tables. Returns their names.

    Only plain file names are written, so a file in the zip can never land outside the folder."""
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    names = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        for name in archive.namelist():
            if "/" in name or "\\" in name or not name.endswith(".txt"):
                continue
            (folder / name).write_bytes(archive.read(name))
            names.append(name)
    return sorted(names)


def date_range(folder: Path) -> tuple[str, str] | None:
    """The first and last day any train runs (YYYYMMDD), from calendar.txt and calendar_dates.txt."""
    days = []
    calendar = folder / "calendar.txt"
    if calendar.exists():
        for row in csv.DictReader(calendar.open(encoding="utf-8-sig")):
            days += [row["start_date"], row["end_date"]]
    calendar_dates = folder / "calendar_dates.txt"
    if calendar_dates.exists():
        for row in csv.DictReader(calendar_dates.open(encoding="utf-8-sig")):
            if row["exception_type"] == "1":
                days.append(row["date"])
    return (min(days), max(days)) if days else None


def download(feed: Feed, gtfs_dir: Path = GTFS_DIR) -> str:
    """Download one feed, unpack it, and return a one-line report."""
    response = httpx.get(feed.url, follow_redirects=True, timeout=120)
    response.raise_for_status()
    names = unpack(response.content, gtfs_dir / feed.name)
    days = date_range(gtfs_dir / feed.name)
    covers = f"{days[0]} to {days[1]}" if days else "no dates found"
    size = len(response.content) / 1_000_000
    return f"{feed.name}: {size:.1f} MB, {len(names)} tables, trains from {covers}"


def main() -> None:
    for feed in FEEDS:
        print(download(feed))


if __name__ == "__main__":
    main()
