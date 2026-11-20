import dice_input

R, K = dice_input.ROLL_SCREEN, dice_input.CONFIG_SCREEN


def started():
    m = dice_input.InputMapper()
    m.actions(R, set(), set(), 0)
    return m


def test_launch_press_ignored():
    m = dice_input.InputMapper()
    assert m.actions(R, {"B"}, {"B"}, 0) == []
    assert m.actions(R, {"B"}, {"B"}, 399) == []
    assert m.actions(R, {"B"}, {"B"}, 400) == [dice_input.CONFIGURE]


def test_up_held_from_launch_never_unlocks_all():
    m = dice_input.InputMapper()
    m.actions(R, {"UP"}, {"UP"}, 0)
    assert all(m.actions(R, set(), {"UP"}, t) == [] for t in range(100, 3000, 100))


def test_roll_screen_mapping():
    m = started()
    got = [m.actions(R, {b}, {b}, 1000 + i)[0] for i, b in enumerate(["A", "C", "UP", "DOWN", "B"])]
    assert got == ["left", "right", "lock", "roll", "configure"]


def test_config_screen_mapping():
    m = started()
    got = [m.actions(K, {b}, {b}, 1000 + i)[0] for i, b in enumerate(["A", "C", "UP", "DOWN", "B"])]
    assert got == ["left", "right", "inc", "dec", "accept"]


def test_long_up_fires_once():
    m = started()
    assert m.actions(R, {"UP"}, {"UP"}, 1000) == ["lock"]
    assert m.actions(R, set(), {"UP"}, 1799) == []
    assert m.actions(R, set(), {"UP"}, 1800) == ["unlock_all"]
    assert m.actions(R, set(), {"UP"}, 2600) == []


def test_release_restarts_long_press():
    m = started()
    m.actions(R, {"UP"}, {"UP"}, 1000)
    m.actions(R, set(), set(), 1300)
    m.actions(R, {"UP"}, {"UP"}, 1400)
    assert m.actions(R, set(), {"UP"}, 2100) == []
    assert m.actions(R, set(), {"UP"}, 2200) == ["unlock_all"]


def test_no_unlock_all_on_config_screen():
    m = started()
    m.actions(K, {"UP"}, {"UP"}, 1000)
    assert m.actions(K, set(), {"UP"}, 2000) == []


def test_same_frame_order():
    m = started()
    held = {"B", "A", "DOWN"}
    assert m.actions(R, set(held), held, 1000) == ["left", "roll", "configure"]
