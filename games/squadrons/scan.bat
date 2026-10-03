@echo off
cd /d "%~dp0..\.."
python -m games.squadrons --scan %*
pause
