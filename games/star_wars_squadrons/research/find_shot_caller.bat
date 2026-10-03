@echo off
rem Step 3: the per-shot method is only called through a vtable - who calls it? Result: one caller, 0x1417b4c0b.
cd /d "%~dp0..\..\.."
python tools\re\retspy.py starwarssquadrons_launcher.exe 0x1418849c0 8 150
pause
