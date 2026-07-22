from bubble_cli import update


def test_shows_versions_between_old_and_current():
    entries = update.whats_new_since("0.1.4", "pt")
    assert entries and entries[0][0] == "0.1.5"
    assert "paralelo" in entries[0][1][0]


def test_nothing_when_already_current():
    from bubble_cli import __version__
    assert update.whats_new_since(__version__, "en") == []


def test_falls_back_to_english_for_unknown_lang():
    entries = update.whats_new_since("0.1.0", "de")
    assert entries and entries[0][1] == update.CHANGELOG["0.1.5"]["en"]
