@echo off
cd /d "%~dp0..\.."
python -m dualsense.profile games\_template\dsx_profile.toml --activate %*
pause
