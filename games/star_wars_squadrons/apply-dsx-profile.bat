@echo off
cd /d "%~dp0..\.."
python -m dualsense.profile games\star_wars_squadrons\dsx_profile.toml --activate %*
pause
