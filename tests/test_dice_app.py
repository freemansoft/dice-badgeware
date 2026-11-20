import dice_app
import dice_config
from dice_input import (
    ACCEPT, CONFIG_SCREEN, CONFIGURE, DEC, INC, LEFT, LOCK, RIGHT, ROLL, ROLL_SCREEN, UNLOCK_ALL,
)


def make(count=4, faces=None, v=3):
    box = [v]
    a = dice_app.DiceApp(
        dice_config.repair({"count": count, "faces": faces or [6] * 6}),
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


def test_left_right_wrap():
    a = make(count=4)
    a.apply(LEFT, 1)
    assert a.cursor == 3
    a.apply(RIGHT, 2)
    assert a.cursor == 0


def test_right_crosses_rows():
    a = make(count=6)
    for t in range(3):
        a.apply(RIGHT, t)
    assert a.cursor == 3


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
    a.apply(INC, 3)
    assert a.faces[3] == 12 and a.count == 4


def test_accept_after_fewer_dice_resets_highlight():
    a = make(count=6)
    for t in range(5):
        a.apply(RIGHT, t)
    assert a.cursor == 5
    a.apply(CONFIGURE, 10)
    a.apply(DEC, 11)
    a.apply(DEC, 12)
    a.apply(ACCEPT, 13)
    assert a.screen == ROLL_SCREEN and a.cursor == 0 and len(a.dice) == 4
    assert a.rolled == [0, 1, 2, 3] and a.rolled_at == 13
    assert not any(d.locked for d in a.dice.dice)
    a.apply(LOCK, 14)


def test_accept_uses_new_faces():
    a = make(count=2)
    a.apply(CONFIGURE, 1)
    a.apply(RIGHT, 2)
    a.apply(INC, 3)
    a.apply(ACCEPT, 4)
    assert [d.faces for d in a.dice.dice] == [7, 6]


def test_take_save():
    a = make(count=4)
    assert a.take_save() is None
    a.apply(CONFIGURE, 1)
    a.apply(ACCEPT, 2)
    assert a.take_save() is None
    a.apply(CONFIGURE, 3)
    a.apply(INC, 4)
    a.apply(ACCEPT, 5)
    assert a.take_save() == {"count": 5, "faces": [6] * 6}
    assert a.take_save() is None


def test_changes_counter():
    a = make()
    c = a.changes
    a.apply(INC, 1)
    assert a.changes == c
    a.apply(RIGHT, 2)
    assert a.changes == c + 1
