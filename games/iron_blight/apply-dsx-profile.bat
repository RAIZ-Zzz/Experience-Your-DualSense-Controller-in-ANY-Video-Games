@echo off
cd /d "%~dp0..\.."
python -m dualsense.profile games\iron_blight\dsx_profile.toml --activate %*
pause
