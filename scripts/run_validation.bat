@echo off
REM =========================================================================
REM  SysML v2 Model Validation Launcher
REM
REM  Locates the Anaconda Python installation and runs validate_model.py
REM  with all arguments forwarded.
REM
REM  Usage:
REM    scripts\run_validation.bat
REM    scripts\run_validation.bat --dry-run
REM    scripts\run_validation.bat --verbose --viz-elements SaturnV
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
echo Searched:
echo   - %%CONDA_PREFIX%%\python.exe
echo   - %%LOCALAPPDATA%%\anaconda3\python.exe
echo   - %%USERPROFILE%%\anaconda3\python.exe
echo   - C:\ProgramData\anaconda3\python.exe
echo   - %%USERPROFILE%%\miniconda3\python.exe
echo   - python (PATH)
exit /b 1

:found
echo Using Python: %PYTHON_EXE%

REM --- Verify JAVA_HOME or java on PATH ---
if not defined JAVA_HOME (
    where java >nul 2>&1
    if %ERRORLEVEL% neq 0 (
        echo WARNING: JAVA_HOME is not set and java is not on PATH.
        echo The SysML kernel requires Java 17+.
    )
)

REM --- Resolve script path (handles running from any directory) ---
set "SCRIPT_DIR=%~dp0"
set "VALIDATE_SCRIPT=%SCRIPT_DIR%validate_model.py"

if not exist "%VALIDATE_SCRIPT%" (
    echo ERROR: Could not find validate_model.py at %VALIDATE_SCRIPT%
    exit /b 1
)

REM --- Run the validator with all forwarded arguments ---
echo.
"%PYTHON_EXE%" "%VALIDATE_SCRIPT%" %*

exit /b %ERRORLEVEL%
