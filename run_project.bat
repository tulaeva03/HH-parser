@echo off
chcp 65001 > nul
set DATA_FILE=hh_business_analyst_vacancies.json

echo ====================================================
echo    ДИАГНОСТИКА ЗАПУСКА
echo ====================================================

:: 1. Проверка Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ОШИБКА] Python не найден в системе. 
    echo Убедитесь, что при установке Python вы нажали галочку "Add to PATH".
    pause
    exit /b
)
echo [+] Python обнаружен.

:: 2. Установка библиотек (без скрытия ошибок)
echo [1/3] Проверка библиотек...
pip install pandas plotly dash dash-bootstrap-components requests numpy
if %errorlevel% neq 0 (
    echo [ОШИБКА] Не удалось установить библиотеки через pip.
    pause
    exit /b
)
echo [+] Библиотеки проверены.
echo ----------------------------------------------------
echo СЛЕДУЮЩИЙ ШАГ: РАБОТА С ФАЙЛАМИ
pause

:: 3. Проверка файлов в папке
if not exist dashboard.py (
    echo [ОШИБКА] Файл dashboard.py не найден в этой папке!
    dir
    pause
    exit /b
)

:: 4. Логика данных
if exist %DATA_FILE% (
    echo [+] Файл с данными найден.
    set /p refresh="Обновить данные с HH.ru? (y - да, любая другая клавиша - нет): "
) else (
    echo [!] Файла данных нет. Запускаю парсер...
    python hh_parser.py
    if %errorlevel% neq 0 (
        echo [ОШИБКА] Ошибка внутри hh_parser.py
        pause
        exit /b
    )
    goto launch
)

if /i "%refresh%"=="y" (
    echo [2/3] Запуск обновления данных...
    python hh_parser.py
)

:launch
echo ----------------------------------------------------
echo СЛЕДУЮЩИЙ ШАГ: ЗАПУСК ДАШБОРДА
pause

echo [3/3] Запуск dashboard.py...
python dashboard.py

if %errorlevel% neq 0 (
    echo.
    echo [ОШИБКА] Дашборд завершился с ошибкой. Проверьте код выше.
)

echo ----------------------------------------------------
echo Работа скрипта завершена.
pause