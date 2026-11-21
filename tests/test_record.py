import pytest
from game.app import DiceApp
from game.controls import ROLL as ROLL_ACTION
from saving import record


def repair_count(c):
    return record.repair({"count": c, "faces": [6] * 6})["count"]


def test_defaults():
    assert record.defaults() == {"count": 4, "faces": [6] * 6}


def test_defaults_are_fresh():
    a = record.defaults()
    a["faces"][0] = 9
    assert record.defaults()["faces"][0] == 6


def test_count_clamped():
    assert [repair_count(c) for c in (0, 1, -3, 7, 99)] == [2, 2, 2, 6, 6]


def test_count_not_numeric():
    assert [repair_count(c) for c in ("x", None, True, [3])] == [4, 4, 4, 4]


def test_count_not_finite():
    assert [repair_count(c) for c in (float("inf"), float("nan"))] == [4, 4]


def test_faces_clamped():
    got = record.repair({"count": 6, "faces": [2, 50, 4, 20, 3, 21]})
    assert got["faces"] == [4, 20, 4, 20, 4, 20]


def test_faces_padded_and_trimmed():
    assert record.repair({"count": 2, "faces": [8]})["faces"] == [8, 6, 6, 6, 6, 6]
    assert record.repair({"count": 2, "faces": [8] * 9})["faces"] == [8] * 6


def test_faces_bad_items():
    got = record.repair({"count": 2, "faces": ["d6", None, False, 7.9, 12, 6]})
    assert got["faces"] == [6, 6, 6, 7, 12, 6]


def test_not_a_dict():
    assert record.repair("garbage") == record.defaults()


def test_faces_not_a_list():
    assert record.repair({"count": 3, "faces": 8}) == {"count": 3, "faces": [6] * 6}


def test_missing_keys():
    assert record.repair({}) == record.defaults()


def test_input_not_mutated():
    d = {"count": 0, "faces": [1]}
    record.repair(d)
    assert d == {"count": 0, "faces": [1]}


ROLL = {"count": 4, "faces": [4, 20, 6, 8, 10, 12], "values": [3, 5, 1, 6, 2, 2],
        "locked": [False, True, False, False, False, False]}


@pytest.mark.parametrize("valid", [
    pytest.param({"count": 2, "faces": [4, 20, 6, 8, 10, 12]}, id="setup only, as in an older file"),
    pytest.param(ROLL, id="with a saved roll"),
])
def test_valid_record_kept_as_is(valid):
    assert record.repair(valid) == valid


@pytest.mark.parametrize("values", [[1, 2, 3], "x", None, [1] * 7])
def test_bad_values_mean_no_roll(values):
    r = record.repair({**ROLL, "values": values})
    assert "values" not in r and "locked" not in r


def test_values_clamped_to_their_faces():
    r = record.repair({"count": 6, "faces": [4, 20, 6, 6, 6, 6],
                            "values": [9, 0, "x", 6, None, 2.7], "locked": [False] * 6})
    assert r["values"] == [4, 1, 1, 6, 1, 2]


def test_locked_only_true_counts():
    r = record.repair({**ROLL, "locked": [True, 1, "yes", None, False, True]})
    assert r["locked"] == [True, False, False, False, False, True]


@pytest.mark.parametrize("locked", [None, [True], "x"])
def test_bad_locked_means_unlocked(locked):
    data = dict(ROLL)
    if locked is None:
        del data["locked"]
    else:
        data["locked"] = locked
    assert record.repair(data)["locked"] == [False] * 6


def test_snapshot_takes_the_setup_dice_and_locks():
    app = DiceApp(record.repair({"count": 3, "faces": [8, 6, 6, 6, 6, 6]}), lambda lo, hi: 3)
    app.dice.dice[1].locked = True
    assert record.snapshot(app, {}) == {"count": 3, "faces": [8, 6, 6, 6, 6, 6],
                                        "values": [3, 3, 3, 1, 1, 1],
                                        "locked": [False, True, False, False, False, False]}


def test_snapshot_keeps_hidden_slots_from_the_previous_record():
    previous = record.repair({**ROLL, "count": 2, "locked": [False, False, True, False, False, True]})
    app = DiceApp(previous, lambda lo, hi: 1)
    app.apply(ROLL_ACTION, 0)
    saved = record.snapshot(app, previous)
    assert saved["values"] == [1, 1, 1, 6, 2, 2]
    assert saved["locked"] == [False, False, True, False, False, True]
