@echo off
cd /d "%~dp0"
echo Building Launcher...
python -m PyInstaller --noconfirm Launcher.spec
echo Building MerlinMakro...
python -m PyInstaller --noconfirm MerlinMakro.spec
copy /Y dist\Launcher.exe Launcher.exe
copy /Y dist\MerlinMakro.exe MerlinMakro.exe
echo Done. EXE files updated in project root.
