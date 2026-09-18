@echo off
cd /d "%~dp0"
set "PATH=%~dp0bin\win-x64;%~dp0bin\kiwix;%~dp0portable-python;%PATH%"
set "PY=%~dp0portable-python\python.exe"
if not exist "%PY%" set "PY=python"
echo Checking Research-in-a-Stick offline model...
"%PY%" -c "from ris import local_llm; print(local_llm.status()); print('ensure', local_llm.ensure_ready(120)); print(local_llm.status()); print(local_llm.chat([{'role':'user','content':'Say ready in one word.'}], max_tokens=16, timeout=60))"
pause
