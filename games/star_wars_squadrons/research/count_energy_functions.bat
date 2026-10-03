@echo off
rem Step 2: hook the 5 energy functions for 3 min while you fire (taps, hold to empty, recharge). Result: only 0x1418849c0 runs, once per shot.
cd /d "%~dp0..\..\.."
python tools\re\count_calls.py starwarssquadrons_launcher.exe 180 0x1418849c0:8:rcx 0x1418847d0:8:rcx 0x141884820:8:rcx 0x141883010:8:rcx 0x141883ce0:6:rcx
pause
