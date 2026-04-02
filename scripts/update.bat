@echo off
chcp 65001 >nul
echo.
echo ========================================
echo   Обновление каталога товаров
echo ========================================
echo.
python "%~dp0upload.py"
echo.
if %ERRORLEVEL% EQU 0 (
    echo Готово! Каталог обновлён.
) else (
    echo ОШИБКА! Проверьте сообщения выше.
)
echo.
pause
