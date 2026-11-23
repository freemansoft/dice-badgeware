"""Die and DiceSet details that DiceApp's tests (test_app.py) can't see:
the range a die rolls over, and the total. Locking, unlocking and rolling
only the unlocked dice are tested through DiceApp, which uses them."""

from game import dice


def fixed(v):
    return lambda _lo, _hi: v


def test_die_roll_uses_one_to_faces():
    calls = []
    d = dice.Die(20)
    assert d.roll(lambda lo, hi: calls.append((lo, hi)) or 17) is True
    assert calls == [(1, 20)]
    assert d.value == 17


def test_total_counts_every_die_locked_or_not():
    s = dice.DiceSet([6, 20, 4])
    s.roll_unlocked(fixed(3))
    s.dice[1].value = 15
    s.toggle_lock(1)
    assert s.total() == 21
    assert len(s) == 3
