from pathlib import Path
from zipfile import ZipFile

from niefiltrowany_export import (
    ass_escape,
    make_zip,
    safe_caption,
    write_commentary_ass,
)


def test_safe_caption_compacts_whitespace_and_limits_length():
    assert safe_caption("  Co\n   dalej?  ") == "Co dalej?"
    assert safe_caption("abcdef", 3) == "abc"


def test_ass_escape_does_not_leave_user_override_tags():
    assert ass_escape("{\\pos(1,2)}") == r"\{\\pos(1,2)\}"
    assert ass_escape("A\nB") == r"A\NB"


def test_commentary_ass_labels_editorial_text(tmp_path: Path):
    ass_file = tmp_path / "commentary.ass"
    write_commentary_ass(ass_file, "To komentarz {nie cytat} polityka.", 7.0)
    content = ass_file.read_text(encoding="utf-8-sig")
    assert "KOMENTARZ" in content
    assert r"\{nie cytat\}" in content
    assert "0:00:07.00" in content


def test_zip_contains_clips_with_no_absolute_paths(tmp_path: Path):
    folder = tmp_path / "clip_01"
    folder.mkdir()
    sample = folder / "sample.txt"
    sample.write_text("test", encoding="utf-8")
    target = make_zip([sample], tmp_path / "all.zip")
    with ZipFile(target) as z:
        assert z.namelist() == ["clip_01/sample.txt"]
        assert z.read("clip_01/sample.txt") == b"test"
