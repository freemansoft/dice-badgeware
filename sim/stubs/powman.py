# Simulator stand-in for the firmware's C powman module (power management).
# Sleep isn't modelled: the badge always reports a RESET wake, and sleep
# calls just yield to the host so the page stays responsive.

import time

WAKE_BUTTON_A = 0
WAKE_BUTTON_B = 1
WAKE_BUTTON_C = 2
WAKE_BUTTON_UP = 3
WAKE_BUTTON_DOWN = 4
WAKE_DOUBLETAP = 5
WAKE_USER_SW = 6
WAKE_VBUS_DETECT = 7
WAKE_RTC = 8
WAKE_ALARM = 9
WAKE_RESET = 241
WAKE_WATCHDOG = 242
WAKE_UNKNOWN = 255


def get_wake_reason():
    return WAKE_RESET


def get_wake_buttons():
    return []


def sleep():
    time.sleep_ms(10)


def goto_dormant_for(_duration):
    time.sleep_ms(10)
