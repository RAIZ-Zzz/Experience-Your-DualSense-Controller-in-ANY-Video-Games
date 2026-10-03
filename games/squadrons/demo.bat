@echo off
cd /d "%~dp0..\.."
python -m games.squadrons --demo %*
pause
