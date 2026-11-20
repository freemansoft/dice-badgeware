# Simulator boot: load the real Badgeware firmware package, then launch the
# Dice Roller app directly (no menu). The host page / headless runner runs
# this after writing the staged files into the MicroPython filesystem.

import board
import machine
import os
import sys

# The simulator's board module has no RTC alarm pin; rtc.alarm_status()
# reads it. The hosts report it high, the firmware's "no alarm" state.
if not hasattr(board, "RTC_ALARM"):
    board.RTC_ALARM = machine.Pin("RTC_ALARM")

os.chdir("/")
sys.path.insert(0, "/lib")      # stand-ins for C modules: powman, pcf85063a
sys.path.insert(0, "/frozen")   # the firmware's badgeware package (see stage.py)

import badgeware  # noqa: E402, F401

launch("/system/apps/dice_roller")
