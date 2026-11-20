import dice_layout


def test_tufty_six():
    assert dice_layout.grid_slots(320, 240, 6) == [
        (64, 84, 40), (160, 84, 40), (256, 84, 40),
        (64, 180, 40), (160, 180, 40), (256, 180, 40),
    ]


def test_tufty_four_is_two_by_two():
    assert dice_layout.grid_slots(320, 240, 4) == [
        (112, 84, 40), (208, 84, 40), (112, 180, 40), (208, 180, 40),
    ]


def test_tufty_five_is_three_then_two():
    assert dice_layout.grid_slots(320, 240, 5) == [
        (64, 84, 40), (160, 84, 40), (256, 84, 40), (112, 180, 40), (208, 180, 40),
    ]


def test_tufty_two_and_three_are_one_row():
    assert dice_layout.grid_slots(320, 240, 2) == [(112, 132, 40), (208, 132, 40)]
    assert dice_layout.grid_slots(320, 240, 3) == [(64, 132, 40), (160, 132, 40), (256, 132, 40)]


def test_menu_lores_six_matches_menu():
    assert dice_layout.grid_slots(160, 120, 6) == [
        (32, 42, 20), (80, 42, 20), (128, 42, 20),
        (32, 90, 20), (80, 90, 20), (128, 90, 20),
    ]


def test_every_count_fits_below_header():
    for w, h in ((320, 240), (264, 176)):
        for n in range(2, 7):
            slots = dice_layout.grid_slots(w, h, n)
            assert len(slots) == n
            for cx, cy, half in slots:
                assert cx - half >= 0 and cx + half <= w
                assert cy - half >= 24 and cy + half <= h
