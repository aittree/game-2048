"""storage 单测：排行榜截断与排序、旧存档兼容、0 分不入榜、设置往返。"""

import json

import pytest

from src import storage


@pytest.fixture(autouse=True)
def temp_save(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "APP_DIR", tmp_path)
    monkeypatch.setattr(storage, "SAVE_FILE", tmp_path / "save.json")


def make_profile(scores):
    return storage.Profile(
        leaderboard=[storage.Record(name=f"p{i}", score=s) for i, s in enumerate(scores)]
    )


def test_legacy_best_only_file():
    storage.SAVE_FILE.write_text(json.dumps({"best": 1234}), encoding="utf-8")
    profile = storage.load_profile()
    assert profile.best == 1234
    assert profile.leaderboard == []
    assert profile.fullscreen is False


def test_insert_keeps_top_ten():
    profile = make_profile(range(100, 110))
    assert storage.insert_record(profile, "new", 1000) == 0
    assert len(profile.leaderboard) == 10
    assert profile.leaderboard[0].name == "new"
    assert profile.leaderboard[-1].score == 101


def test_record_below_threshold_rejected():
    profile = make_profile(range(100, 110))
    assert storage.qualifies(profile, 100) is False
    assert storage.insert_record(profile, "low", 100) is None
    assert len(profile.leaderboard) == 10


def test_equal_score_keeps_earlier_first():
    profile = make_profile([50, 40])
    assert storage.insert_record(profile, "late", 50) == 1
    assert [r.name for r in profile.leaderboard] == ["p0", "late", "p1"]


def test_zero_score_not_qualified():
    profile = storage.Profile()
    assert storage.qualifies(profile, 0) is False
    assert storage.insert_record(profile, "zero", 0) is None


def test_roundtrip_settings_and_records():
    profile = storage.Profile(
        best=512,
        fullscreen=True,
        leaderboard=[storage.Record("a", 512, "2026-01-01 10:00")],
    )
    storage.save_profile(profile)
    loaded = storage.load_profile()
    assert loaded.best == 512
    assert loaded.fullscreen is True
    assert loaded.leaderboard == [storage.Record("a", 512, "2026-01-01 10:00")]
