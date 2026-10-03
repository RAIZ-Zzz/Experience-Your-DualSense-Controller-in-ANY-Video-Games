@echo off
cd /d "%~dp0..\.."
python -m games._template %*
pause
