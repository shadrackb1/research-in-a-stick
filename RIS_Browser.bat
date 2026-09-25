@echo off
title RIS Browser
cd /d "%~dp0"
set "EXE="
for /f "delims=" %%F in ('dir /b /s "%~dp0browser\chrome.exe" 2^>nul') do (
  if not defined EXE set "EXE=%%F"
)
if not defined EXE (
  echo RIS Browser engine not found under browser\
  pause
  exit /b 1
)
start "" "%EXE%" ^
  --user-data-dir="%~dp0browser\profile" ^
  --no-first-run --no-default-browser-check ^
  --homepage="http://127.0.0.1:8765/search" ^
  "http://127.0.0.1:8765/search"
