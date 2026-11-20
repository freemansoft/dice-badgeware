import dice_layout

# The Tufty's dice area: below a 32 px header, left of a 56 px label column,
# above a 28 px label bar.
AREA = (264, 180, 0, 32)


def slots(count, area=AREA):
    w, h, left, top = area
    return dice_layout.grid_slots(w, h, count, left, top)


def test_six_is_three_by_two():
    # the menu's spacing, scaled: min(264 / 144, 180 / 96) = 1.833, so its
    # 48 px cells become 88 px and its 20 px icon half-size 37 px
    assert slots(6) == [(44, 78, 37), (132, 78, 37), (220, 78, 37), (44, 166, 37), (132, 166, 37), (220, 166, 37)]


def test_four_is_two_by_two():
    assert slots(4) == [(88, 78, 37), (176, 78, 37), (88, 166, 37), (176, 166, 37)]


def test_five_is_three_then_two():
    assert slots(5) == [(44, 78, 37), (132, 78, 37), (220, 78, 37), (88, 166, 37), (176, 166, 37)]


def test_two_and_three_are_one_centred_row():
    assert slots(2) == [(88, 122, 37), (176, 122, 37)]
    assert slots(3) == [(44, 122, 37), (132, 122, 37), (220, 122, 37)]


def test_area_defaults_to_the_origin():
    assert dice_layout.grid_slots(264, 180, 4) == [(88, 46, 37), (176, 46, 37), (88, 134, 37), (176, 134, 37)]


def test_every_count_fits_in_its_area():
    for w, h, left, top in (AREA, (264, 176, 0, 0), (200, 100, 10, 20), (39, 26, 0, 0)):
        for n in range(2, 7):
            got = dice_layout.grid_slots(w, h, n, left, top)
            assert len(got) == n
            for cx, cy, half in got:
                assert left <= cx - half and cx + half <= left + w
                assert top <= cy - half and cy + half <= top + h
