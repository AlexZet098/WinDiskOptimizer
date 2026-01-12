@echo off
REM Build GUI and CLI executables for Windows 10/11
SETLOCAL

IF NOT EXIST ..\venv (
    echo Creating local virtual environment...
    python -m venv ..\venv || exit /b 1
)

CALL ..\venv\Scripts\activate || exit /b 1
python -m pip install --upgrade pip || exit /b 1
python -m pip install -r ..\requirements.txt pyinstaller || exit /b 1

pyinstaller --clean --noconfirm ..\WinDiskOptimizer.spec || exit /b 1

echo Executables are in dist\WinDiskOptimizer\WinDiskOptimizer.exe (GUI) and dist\WinDiskOptimizerCLI\WinDiskOptimizerCLI.exe (CLI)
ENDLOCAL
