@echo off
rem Haptics output paths (no game needed, DSX running): left / right rumble, then balance rounds, then stereo tones.
cd /d "%~dp0..\..\.."
python tools\haptics\rumble_test.py && python tools\haptics\balance_test.py && python tools\haptics\tone_test.py
pause
