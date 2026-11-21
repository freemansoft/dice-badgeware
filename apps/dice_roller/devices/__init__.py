"""Everything badge-specific: how buttons are read (buttons.py) and one
display per badge (tufty.py, badger.py), picked by badge.model.

A display has begin_frame() (before the buttons are read) and
end_frame(app, now) (after the actions are applied). Between them they
own every per-frame step that differs between badges: polling, clearing,
drawing, pushing the frame and waiting. To support another badge, add
its display file here and a line to display_for().
"""


def display_for(model):
    """A new display for this badge model. Only that badge's module is
    imported, so the others cost no memory."""
    if model == "tufty":
        from devices.tufty import TuftyDisplay

        return TuftyDisplay()
    if model == "badger":
        from devices.badger import BadgerDisplay

        return BadgerDisplay()
    from devices.unsupported import UnsupportedDisplay

    return UnsupportedDisplay()
