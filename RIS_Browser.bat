@echo off
title RIS Browser
cd /d "%~dp0"

rem Find bundled ungoogled-chromium (real Chromium engine)
set "EXE="
for /f "delims=" %%F in ('dir /b /s "%~dp0browser\chrome.exe" 2^>nul') do (
  if not defined EXE set "EXE=%%F"
)

if not defined EXE (
  echo RIS Browser engine not found.
  echo Put ungoogled-chromium under browser\ or run tools\install_browser.ps1
  pause
  exit /b 1
)

rem Local profile on the stick + RIS home
start "" "%EXE%" --user-data-dir="%~dp0browser\profile" --no-first-run --no-default-browser-check "http://127.0.0.1:8765"
