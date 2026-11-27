@echo off
rem run.bat - runs the whole project on Windows (double-click it, or press Ctrl+Shift+B in VS Code).
cd /d "%~dp0"
where py >nul 2>nul && (py -3 run_project.py %* & goto :end)
where python >nul 2>nul && (python run_project.py %* & goto :end)
echo Python was not found. Install Python 3 from python.org and run this again.
:end
