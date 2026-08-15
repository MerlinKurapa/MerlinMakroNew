@echo off
cd /d "%~dp0"
echo Cleaning old build files...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist __pycache__ rmdir /s /q __pycache__
if exist _internal rmdir /s /q _internal
echo Building Launcher...
python -m PyInstaller --noconfirm Launcher.spec
echo Building MerlinMakro...
python -m PyInstaller --noconfirm MerlinMakro.spec
copy /Y dist\Launcher.exe Launcher.exe
copy /Y dist\MerlinMakro.exe MerlinMakro.exe
echo Cleaning build directories...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
echo Done. EXE files updated in project root.
