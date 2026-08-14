@echo off
echo Windows ikon onbellegi temizleniyor...
taskkill /f /im explorer.exe >nul 2>&1
del /a /q "%localappdata%\IconCache.db" >nul 2>&1
del /a /q "%localappdata%\Microsoft\Windows\Explorer\iconcache_*.db" >nul 2>&1
start explorer.exe
if exist "%SystemRoot%\System32\ie4uinit.exe" (
  ie4uinit.exe -ClearIconCache >nul 2>&1
)
echo Tamamlandi. Kisa yollari bir kez yeniden olusturman gerekebilir.
