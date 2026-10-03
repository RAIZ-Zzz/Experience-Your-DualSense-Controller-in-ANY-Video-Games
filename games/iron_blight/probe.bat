@echo off
cd /d "%~dp0..\.."
python -m games.iron_blight --probe %*
pause
