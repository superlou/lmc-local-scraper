from datetime import date
from pathlib import Path

from events_ai.gen_path_manager import GenPathManager


def test_create_gen_manager(tmp_path):
    assert GenPathManager("test")
    assert GenPathManager(tmp_path)


def test_gen_manager_create_by_date(tmp_path):
    gpm = GenPathManager(tmp_path)
    today = date(1997, 8, 29)

    assert gpm.by_date(today) == Path(tmp_path) / "1997-08-29"


def test_gen_manager_find_recent(tmp_path):
    gen1 = tmp_path / "1997-08-28"
    gen1.mkdir()

    (tmp_path / "fake").mkdir()

    gen2 = tmp_path / "1997-08-27"
    gen2.mkdir()

    gen3 = tmp_path / "1997-08-25"  # intentionally skip a day
    gen3.mkdir()

    gen4 = tmp_path / "1997-08-24"
    gen4.mkdir()

    gpm = GenPathManager(tmp_path)
    today = date(1997, 8, 29)
    recent = gpm.find_recent(today, 4)
    assert len(recent) == 3
