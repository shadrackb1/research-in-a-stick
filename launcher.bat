@echo off
title Research-in-a-Stick
cd /d "%~dp0"
set "PATH=%~dp0bin\win-x64;%~dp0bin\kiwix;%~dp0portable-python;%PATH%"
set "PY=%~dp0portable-python\python.exe"
if not exist "%PY%" (
  where python >nul 2>nul
  if %errorlevel%==0 (set "PY=python") else (
    where py >nul 2>nul
    if %errorlevel%==0 (set "PY=py -3") else (
      echo Python 3 is required. Install from https://python.org
      pause & exit /b 1
    )
  )
)
echo Starting Research-in-a-Stick...
echo Dashboard: http://127.0.0.1:8765
echo Local AI:  models\ + bin\win-x64\
echo Offline wiki: wiki\*.zim via bin\kiwix\kiwix-serve.exe
"%PY%" start.py
pause
