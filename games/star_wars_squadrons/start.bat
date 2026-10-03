@echo off
cd /d "%~dp0..\.."
python -m games.star_wars_squadrons %*
pause
