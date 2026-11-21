from game import controls

R, K = controls.ROLL_SCREEN, controls.CONFIG_SCREEN


def started():
    m = controls.InputMapper()
    m.actions(R, set(), set(), 0)
    return m


def test_launch_press_ignored():
    m = controls.InputMapper()
    assert m.actions(R, {"B"}, {"B"}, 0) == []
    assert m.actions(R, {"B"}, {"B"}, 399) == []
    assert m.actions(R, {"B"}, {"B"}, 400) == [controls.CONFIGURE]


def test_up_held_from_launch_never_unlocks_all():
    m = controls.InputMapper()
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


def held_up(m, screen, t0, t1, step=20):
    """Frames every `step` ms from t0 up to t1 with UP held, as a badge
    polls; the actions they produced, by time."""
    return {t: a for t in range(t0, t1, step) if (a := m.actions(screen, set(), {"UP"}, t))}


def test_long_up_fires_once():
    m = started()
    assert m.actions(R, {"UP"}, {"UP"}, 1000) == ["lock"]
    assert held_up(m, R, 1020, 2600) == {1800: ["unlock_all"]}


def test_release_restarts_long_press():
    m = started()
    m.actions(R, {"UP"}, {"UP"}, 1000)
    m.actions(R, set(), set(), 1300)
    m.actions(R, {"UP"}, {"UP"}, 1400)
    assert held_up(m, R, 1420, 2400) == {2200: ["unlock_all"]}


def test_a_hold_counts_only_while_watched():
    # On e-ink the lock starts a ~1 s blocking refresh, so the next frame
    # comes a second later with UP down again. That proves nothing: UP may
    # have been tapped a second time. The hold restarts from that frame.
    m = started()
    assert m.actions(R, {"UP"}, {"UP"}, 1000) == ["lock"]
    assert held_up(m, R, 2000, 3000) == {2800: ["unlock_all"]}


def test_no_unlock_all_on_config_screen():
    m = started()
    m.actions(K, {"UP"}, {"UP"}, 1000)
    assert held_up(m, K, 1020, 2600) == {}


def test_same_frame_order():
    m = started()
    held = {"B", "A", "DOWN"}
    assert m.actions(R, set(held), held, 1000) == ["left", "roll", "configure"]


def test_label_words():
    assert controls.LABELS[R] == {"A": "Left", "B": "Setup", "C": "Right", "UP": "Lock", "DOWN": "Roll"}
    assert controls.LABELS[K] == {"A": "Left", "B": "Done", "C": "Right", "UP": "More", "DOWN": "Less"}
    assert controls.HOLD_LABELS == {R: {"UP": "hold: all"}, K: {}}


def test_no_ignore_window_when_woken():
    m = controls.InputMapper(ignore_ms=0)
    assert m.actions(R, {controls.B}, {controls.B}, 0) == [controls.CONFIGURE]
