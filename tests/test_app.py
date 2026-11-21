from game.app import DiceApp
from game.controls import (
    ACCEPT,
    CONFIG_SCREEN,
    CONFIGURE,
    DEC,
    INC,
    LEFT,
    LOCK,
    RIGHT,
    ROLL,
    ROLL_SCREEN,
    UNLOCK_ALL,
)
from saving import record


def make(count=4, faces=None, v=3):
    box = [v]
    a = DiceApp(
        record.repair({"count": count, "faces": faces or [6] * 6}),
        lambda lo, hi: min(box[0], hi),
    )
    a.box = box
    return a


def values(a):
    return [d.value for d in a.dice.dice]


def test_starts_on_roll_screen():
    a = make(count=4)
    assert a.screen == ROLL_SCREEN and a.cursor == 0
    assert len(a.dice) == 4 and values(a) == [3] * 4
    assert a.rolled == [] and a.rolled_at is None


def test_left_right_step_through_every_die_and_wrap():
    # reading order, so stepping from die 3 to die 4 crosses the rows
    a = make(count=6)
    seen = []
    for t in range(6):
        a.apply(RIGHT, t)
        seen.append(a.cursor)
    assert seen == [1, 2, 3, 4, 5, 0]
    a.apply(LEFT, 6)
    assert a.cursor == 5
    a.apply(LEFT, 7)
    assert a.cursor == 4


def test_lock_toggles_highlighted():
    a = make()
    a.apply(RIGHT, 1)
    a.apply(LOCK, 2)
    assert a.dice.dice[1].locked
    a.apply(LOCK, 3)
    assert not a.dice.dice[1].locked


def test_roll_only_unlocked():
    a = make(count=3, v=3)
    a.apply(LOCK, 1)
    a.box[0] = 5
    a.apply(ROLL, 100)
    assert a.rolled == [1, 2] and a.rolled_at == 100
    assert values(a) == [3, 5, 5]


def test_all_locked_roll_changes_nothing():
    a = make(count=2)
    a.apply(LOCK, 1)
    a.apply(RIGHT, 2)
    a.apply(LOCK, 3)
    before = (a.changes, a.rolled_at, values(a))
    a.box[0] = 6
    a.apply(ROLL, 500)
    assert (a.changes, a.rolled_at, values(a)) == before


def test_unlock_all():
    a = make()
    a.apply(LOCK, 1)
    a.apply(RIGHT, 2)
    a.apply(LOCK, 3)
    a.apply(UNLOCK_ALL, 4)
    assert not any(d.locked for d in a.dice.dice)


def test_configure_and_clamps():
    a = make(count=6)
    a.apply(RIGHT, 0)
    a.apply(CONFIGURE, 1)
    assert (a.screen, a.cursor) == (CONFIG_SCREEN, 0)
    a.apply(INC, 2)
    assert a.count == 6
    for t in range(10):
        a.apply(DEC, 3 + t)
    assert a.count == 2
    a.apply(RIGHT, 20)
    for t in range(30):
        a.apply(INC, 21 + t)
    assert a.faces[0] == 20
    for t in range(30):
        a.apply(DEC, 60 + t)
    assert a.faces[0] == 4


def test_config_cursor_wraps_over_count_plus_one():
    a = make(count=2)
    a.apply(CONFIGURE, 1)
    a.apply(LEFT, 2)
    assert a.cursor == 2
    a.apply(RIGHT, 3)
    assert a.cursor == 0


def test_hidden_dice_keep_faces():
    a = make(count=4, faces=[6, 6, 6, 12, 6, 6])
    a.apply(CONFIGURE, 1)
    a.apply(DEC, 2)
    a.apply(ACCEPT, 3)
    assert [d.faces for d in a.dice.dice] == [6, 6, 6]
    assert a.faces == [6, 6, 6, 12, 6, 6]
    a.apply(CONFIGURE, 4)
    a.apply(INC, 5)
    a.apply(ACCEPT, 6)
    assert [d.faces for d in a.dice.dice] == [6, 6, 6, 12]


def test_accept_returns_to_a_fresh_unlocked_roll():
    a = make(count=6, v=3)
    a.apply(LOCK, 0)
    a.apply(CONFIGURE, 10)
    a.apply(DEC, 11)
    a.apply(DEC, 12)
    a.apply(RIGHT, 13)
    a.box[0] = 5
    a.apply(ACCEPT, 14)
    assert a.screen == ROLL_SCREEN and a.cursor == 0 and len(a.dice) == 4
    assert a.rolled == [0, 1, 2, 3] and a.rolled_at == 14
    assert values(a) == [5] * 4
    assert not any(d.locked for d in a.dice.dice)


def test_accept_uses_new_faces():
    a = make(count=2)
    a.apply(CONFIGURE, 1)
    a.apply(RIGHT, 2)
    a.apply(INC, 3)
    a.apply(ACCEPT, 4)
    assert [d.faces for d in a.dice.dice] == [7, 6]


def never(lo, hi):
    raise AssertionError("rolled")


def saved_roll(count=3, values=(2, 5, 4, 1, 1, 1), locked=(False, True) + (False,) * 4):
    return record.repair({"count": count, "faces": [6] * 6,
                          "values": list(values), "locked": list(locked)})


def test_restores_saved_roll_without_rolling():
    a = DiceApp(saved_roll(), never)
    assert values(a) == [2, 5, 4]
    assert [d.locked for d in a.dice.dice] == [False, True, False]
    assert a.rolled == [] and a.rolled_at is None
    assert a.screen == ROLL_SCREEN and a.cursor == 0


def test_save_points_are_rolls_and_accepts_once_each():
    a = make(count=3)
    assert not a.take_save_point()  # the launch roll isn't one
    a.apply(ROLL, 1)
    assert a.take_save_point()
    assert not a.take_save_point()
    a.apply(CONFIGURE, 2)
    a.apply(INC, 3)
    assert not a.take_save_point()  # setup edits wait for Done
    a.apply(ACCEPT, 4)
    assert a.take_save_point()


def test_locks_and_moves_are_not_save_points():
    a = make()
    for action in (LOCK, RIGHT, LOCK, UNLOCK_ALL, LEFT):
        a.apply(action, 0)
    assert not a.take_save_point()


def test_all_locked_roll_is_not_a_save_point():
    a = make(count=2)
    a.apply(LOCK, 0)
    a.apply(RIGHT, 0)
    a.apply(LOCK, 0)
    a.apply(ROLL, 0)
    assert not a.take_save_point()


def test_changes_counter():
    a = make()
    c = a.changes
    a.apply(INC, 1)
    assert a.changes == c
    a.apply(RIGHT, 2)
    assert a.changes == c + 1
