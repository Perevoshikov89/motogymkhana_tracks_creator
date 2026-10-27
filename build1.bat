```bat
@echo off
chcp 65001 > nul
setlocal

title BUILD CREATOR

echo ========================================
echo        BUILD CREATOR
echo ========================================
echo.

echo [1/4] Проверка Python...

where python
if errorlevel 1 (
    echo ERROR: Python not found in PATH.
    pause
    exit /b 1
)

python --version
if errorlevel 1 (
    echo ERROR: Python cannot start.
    pause
    exit /b 1
)

echo.
echo [2/4] Определение clidriver...

for /f "delims=" %%P in ('python -c "import os,sysconfig; print(os.path.join(sysconfig.get_path('purelib'),'clidriver'))"') do set "CLIDRIVER=%%P"

echo CLIDRIVER=%CLIDRIVER%

if not exist "%CLIDRIVER%\bin" (
    echo ERROR: clidriver\bin not found.
    echo Check the clidriver path.
    pause
    exit /b 1
)

if not exist "creator.py" (
    echo ERROR: creator.py not found in the current folder.
    pause
    exit /b 1
)

echo.
echo [3/4] Проверка зависимостей...

python -c "import tkinter; print('Tkinter OK')"
if errorlevel 1 (
    echo ERROR: Tkinter unavailable.
    pause
    exit /b 1
)

python -c "import PyInstaller; print('PyInstaller OK')"
if errorlevel 1 (
    echo ERROR: PyInstaller is not installed.
    pause
    exit /b 1
)

python -c "import ibm_db; print('ibm_db OK')"
if errorlevel 1 (
    echo ERROR: ibm_db import failed.
    pause
    exit /b 1
)

echo.
echo [4/4] Очистка старой сборки...

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist key_checker.spec del /q key_checker.spec

echo.
echo Сборка EXE...
echo.

python -m PyInstaller ^
    --clean ^
    --noconfirm ^
    --onefile ^
    --collect-binaries ibm_db ^
    --add-data "%CLIDRIVER%;clidriver" ^
    key_checker.py

if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller build failed.
    pause
    exit /b 1
)

echo.
echo ========================================

if exist "dist\creator.exe" (
    echo BUILD SUCCESSFUL!
    echo.
    echo EXE:
    echo %CD%\dist\key_checker.exe
    echo.
    echo Запусти EXE и проверь работу программы.
) else (
    echo ERROR: EXE file not found.
)

echo ========================================
pause
endlocal
