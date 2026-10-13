import io
import zipfile

from app.trains.download import date_range, unpack


def make_zip(files: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, text in files.items():
            archive.writestr(name, text)
    return buffer.getvalue()


def test_unpack_keeps_only_plain_txt_tables(tmp_path):
    zip_bytes = make_zip({"stops.txt": "a", "readme.pdf": "b", "../evil.txt": "c", "sub/trips.txt": "d"})
    names = unpack(zip_bytes, tmp_path / "feed")
    assert names == ["stops.txt"]
    assert not (tmp_path / "evil.txt").exists()


def test_unpack_replaces_old_files(tmp_path):
    folder = tmp_path / "feed"
    unpack(make_zip({"old.txt": "x"}), folder)
    unpack(make_zip({"new.txt": "y"}), folder)
    assert sorted(p.name for p in folder.iterdir()) == ["new.txt"]


def test_date_range_uses_calendar_and_added_dates_only(tmp_path):
    (tmp_path / "calendar.txt").write_text("service_id,start_date,end_date\ns1,20261201,20261220\n")
    (tmp_path / "calendar_dates.txt").write_text(
        "service_id,date,exception_type\ns2,20261228,1\ns3,20270105,2\n")
    assert date_range(tmp_path) == ("20261201", "20261228")


def test_date_range_none_without_calendars(tmp_path):
    assert date_range(tmp_path) is None
