"""A badge with no display file yet: show a short message."""


class UnsupportedDisplay:
    """Pushed to the screen once, for badges whose run() loop doesn't
    update the display."""

    def __init__(self):
        self.shown = False

    def begin_frame(self):
        pass

    def end_frame(self, _app, _now):
        screen.pen = color.rgb(255, 255, 255)
        screen.text("Dice Roller:", 1, 1)
        screen.text("{} not".format(badge.model), 1, 12)
        screen.text("supported", 1, 23)
        if not self.shown:
            display.update()
            self.shown = True
