@echo off
rem The brain tool, called short as .agents\brain from cmd or PowerShell, the
rem twin of .agents/brain, which Git Bash runs. The tool finds the brain from
rem the folder it runs in.
python3 "%~dp0skills\agent-brain\scripts\brain.py" %*
exit /b %ERRORLEVEL%
