@echo off
rem Step 1: every instruction writing the energy field +0x2E0 (found 112; the real ones sit near 0x14188xxxx).
cd /d "%~dp0..\..\.."
python tools\re\find_writers.py starwarssquadrons_launcher.exe 2E0
pause
