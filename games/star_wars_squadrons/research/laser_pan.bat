@echo off
rem Is the laser sound panned per cannon? Fire for 2 min. Result: alternates (81 %% flips) but only about +-0.1. Counts every ship's shots, so fire somewhere quiet.
cd /d "%~dp0..\..\.."
python tools\re\audio_pan.py starwarssquadrons_launcher.exe 120 0x1418849c0:8:rcx
pause
