@echo off
cd /d "%~dp0..\.."
python -m dualsense.profile games\squadrons\dsx_profile.toml --activate %*
pause
