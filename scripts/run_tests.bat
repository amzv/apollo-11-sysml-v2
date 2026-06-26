@echo off
REM =========================================================================
REM  SysML Model Validation Tests Launcher
REM
REM  Locates the Anaconda Python installation and runs pytest against the 
REM  tests directory.
REM =========================================================================

setlocal enabledelayedexpansion

REM --- Locate Python via common Anaconda install paths ---
set "PYTHON_EXE="

REM 1. Check CONDA_PREFIX (active conda env)
if defined CONDA_PREFIX (
    if exist "%CONDA_PREFIX%\python.exe" (
        set "PYTHON_EXE=%CONDA_PREFIX%\python.exe"
        goto :found
    )
)

REM 2. User-local Anaconda3 install
if exist "%LOCALAPPDATA%\anaconda3\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\anaconda3\python.exe"
    goto :found
)

REM 3. User profile Anaconda3
if exist "%USERPROFILE%\anaconda3\python.exe" (
    set "PYTHON_EXE=%USERPROFILE%\anaconda3\python.exe"
    goto :found
)

REM 4. ProgramData Anaconda3
if exist "C:\ProgramData\anaconda3\python.exe" (
    set "PYTHON_EXE=C:\ProgramData\anaconda3\python.exe"
    goto :found
)

REM 5. Miniconda variants
if exist "%USERPROFILE%\miniconda3\python.exe" (
    set "PYTHON_EXE=%USERPROFILE%\miniconda3\python.exe"
    goto :found
)

REM 6. Fall back to PATH
where python >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set "PYTHON_EXE=python"
    goto :found
)

echo ERROR: Could not find Python. Please install Anaconda or add Python to PATH.
exit /b 1

:found
echo Using Python: %PYTHON_EXE%

REM --- Resolve paths ---
set "SCRIPT_DIR=%~dp0"
set "REPO_DIR=%SCRIPT_DIR%.."

echo Running pytest...
"%PYTHON_EXE%" -m pytest "%REPO_DIR%\tests" -v %*

exit /b %ERRORLEVEL%
