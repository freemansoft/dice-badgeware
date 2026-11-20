# Simulator stand-in for the firmware's C pcf85063a module (the RTC chip).
# Time comes from the host clock; timers and alarms never fire.

import time


class PCF85063A:
    def __init__(self, _i2c=None):
        pass

    def datetime(self, value=None):
        if value is not None:
            return None
        t = time.localtime()
        return (t[0], t[1], t[2], t[3], t[4], t[5], t[6])

    def enable_timer_interrupt(self, _enable):
        pass

    def set_timer(self, _ticks):
        pass

    def read_timer_flag(self):
        return False

    def clear_timer_flag(self):
        pass

    def clear_alarm_flag(self):
        pass

    def enable_alarm_interrupt(self, _enable):
        pass

    def set_alarm(self, *_args):
        pass

    def unset_alarm(self):
        pass
