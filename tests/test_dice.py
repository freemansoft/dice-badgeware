import dice


def fixed(v):
    return lambda lo, hi: v


def test_die_roll_uses_one_to_faces():
    calls = []
    d = dice.Die(20)
    assert d.roll(lambda lo, hi: calls.append((lo, hi)) or 17) is True
    assert calls == [(1, 20)]
    assert d.value == 17


def test_locked_die_does_not_roll():
    d = dice.Die(6, value=3)
    d.toggle_lock()
    assert d.roll(fixed(5)) is False
    assert d.value == 3


def test_toggle_lock_locks_then_unlocks():
    d = dice.Die(6)
    assert d.locked is False
    d.toggle_lock()
    assert d.locked is True
    d.toggle_lock()
    assert d.locked is False


def test_roll_unlocked_returns_rolled_indices():
    s = dice.DiceSet([6, 6, 6])
    s.toggle_lock(1)
    assert s.roll_unlocked(fixed(4)) == [0, 2]
    assert [d.value for d in s.dice] == [4, 1, 4]


def test_unlock_all():
    s = dice.DiceSet([6, 6])
    s.toggle_lock(0)
    s.toggle_lock(1)
    s.unlock_all()
    assert not any(d.locked for d in s.dice)


def test_total_and_len():
    s = dice.DiceSet([6, 20, 4])
    s.roll_unlocked(fixed(3))
    assert s.total() == 9
    assert len(s) == 3
