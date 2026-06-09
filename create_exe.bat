@echo off
setlocal

set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
pushd "%PROJECT_DIR%" || exit /b 1

set "PYINSTALLER=%PROJECT_DIR%\.venv\Scripts\pyinstaller.exe"

if not exist "%PYINSTALLER%" (
    echo [ERROR] PyInstaller not found:
    echo "%PYINSTALLER%"
    echo.
    echo Install it with:
    echo ".\.venv\Scripts\python.exe" -m pip install pyinstaller
    popd
    exit /b 1
)

echo Cleaning build and dist...
if exist build rmdir /S /Q build
if exist dist rmdir /S /Q dist

echo Building main.exe...
"%PYINSTALLER%" --noconfirm --clean "main.spec"
if errorlevel 1 (
    echo [ERROR] main.exe build failed.
    pause
    popd
    exit /b 1
)

echo Building SaveSetup.exe...
"%PYINSTALLER%" --noconfirm --clean "save_setup.spec"
if errorlevel 1 (
    echo [ERROR] SaveSetup.exe build failed.
    pause
    popd
    exit /b 1
)

echo Copying _internal...
set "SRC_INTERNAL=_internal"
set "DEST_DIST=dist\_internal"

if exist "%SRC_INTERNAL%" (
    if exist "%DEST_DIST%" rmdir /S /Q "%DEST_DIST%"
    xcopy "%SRC_INTERNAL%" "%DEST_DIST%\" /E /I /Y > copy.log
    if errorlevel 1 (
        echo [ERROR] Failed to copy _internal.
        pause
        popd
        exit /b 1
    )
) else (
    echo [WARNING] Folder _internal not found.
)

echo.
echo Done:
echo   dist\main.exe
echo   dist\SaveSetup.exe
pause

popd
endlocal
