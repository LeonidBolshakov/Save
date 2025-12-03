@echo off
setlocal

echo Очистка build и dist...
if exist build rmdir /S /Q build
if exist dist  rmdir /S /Q dist

echo Сборка EXE...
".\.venv\Scripts\pyinstaller.exe" save_setup.spec
if errorlevel 1 (
    echo [ОШИБКА] PyInstaller завершился с ошибкой.
    pause
    exit /b 1
)

echo Копирование _internal...
set "SRC_INTERNAL=_internal"
set "DEST_DIST=dist\_internal"
if exist "%SRC_INTERNAL%" (
    xcopy "%SRC_INTERNAL%" "%DEST_DIST%\" /E /I /Y > copy.log
) else (
    echo [ПРЕДУПРЕЖДЕНИЕ] Папка _internal не найдена.
)

echo Готово: dist\SaveSetup.exe
pause
