"""Run the real app on the Badger 2350 in the badgeware-wasm simulator."""

from simrun import needs_node, simulate

pytestmark = needs_node


def test_badger_boots_and_draws(tmp_path):
    result = simulate("badger", "", tmp_path / "f.json")
    assert (result["width"], result["height"]) == (264, 176)
    assert len(result["frames"]) == 1
