import dice_config


def repair_count(c):
    return dice_config.repair({"count": c, "faces": [6] * 6})["count"]


def test_defaults():
    assert dice_config.defaults() == {"count": 4, "faces": [6] * 6}


def test_defaults_are_fresh():
    a = dice_config.defaults()
    a["faces"][0] = 9
    assert dice_config.defaults()["faces"][0] == 6


def test_valid_kept():
    d = {"count": 2, "faces": [4, 20, 6, 8, 10, 12]}
    assert dice_config.repair(d) == d


def test_count_clamped():
    assert [repair_count(c) for c in (0, 1, -3, 7, 99)] == [2, 2, 2, 6, 6]


def test_count_not_numeric():
    assert [repair_count(c) for c in ("x", None, True, [3])] == [4, 4, 4, 4]


def test_count_not_finite():
    assert [repair_count(c) for c in (float("inf"), float("nan"))] == [4, 4]


def test_faces_clamped():
    got = dice_config.repair({"count": 6, "faces": [2, 50, 4, 20, 3, 21]})
    assert got["faces"] == [4, 20, 4, 20, 4, 20]


def test_faces_padded_and_trimmed():
    assert dice_config.repair({"count": 2, "faces": [8]})["faces"] == [8, 6, 6, 6, 6, 6]
    assert dice_config.repair({"count": 2, "faces": [8] * 9})["faces"] == [8] * 6


def test_faces_bad_items():
    got = dice_config.repair({"count": 2, "faces": ["d6", None, False, 7.9, 12, 6]})
    assert got["faces"] == [6, 6, 6, 7, 12, 6]


def test_not_a_dict():
    assert dice_config.repair("garbage") == dice_config.defaults()


def test_faces_not_a_list():
    assert dice_config.repair({"count": 3, "faces": 8}) == {"count": 3, "faces": [6] * 6}


def test_missing_keys():
    assert dice_config.repair({}) == dice_config.defaults()


def test_input_not_mutated():
    d = {"count": 0, "faces": [1]}
    dice_config.repair(d)
    assert d == {"count": 0, "faces": [1]}
