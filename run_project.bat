@echo off
chcp 65001 > nul
set DATA_FILE=hh_business_analyst_vacancies.json

echo ====================================================
echo    АВТОМАТИЧЕСКИЙ УСТАНОВЩИК И ЗАПУСК (2026)
echo ====================================================

:: 1. ПРОВЕРКА И УСТАНОВКА PYTHON (Улучшение логики [cite: 1])
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Python не найден. Начинаю загрузку...
    :: Скачиваем установщик через системный curl
    curl -L -o py_inst.exe https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe
    echo [*] Установка Python в тихом режиме...
    :: Установка с автоматическим добавлением в PATH
    start /wait py_inst.exe /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
    del py_inst.exe
    echo [+] Python установлен. Перезапустите этот файл.
    pause
    exit /b
)
echo [+] Python обнаружен.

:: 2. СОЗДАНИЕ ВИРТУАЛЬНОГО ОКРУЖЕНИЯ (Решение проблемы "невидимых" библиотек)
if not exist "venv" (
    echo [*] Создание изолированной среды для библиотек...
    python -m venv venv
)

:: 3. УСТАНОВКА БИБЛИОТЕК ВНУТРИ СРЕДЫ (Улучшение логики [cite: 2])
echo [*] Проверка и обновление библиотек...
call venv\Scripts\activate
python -m pip install --upgrade pip >nul
pip install pandas plotly dash dash-bootstrap-components requests numpy

:: 4. ПРОВЕРКА ФАЙЛОВ ПРОЕКТА [cite: 3]
if not exist dashboard.py (
    echo [ОШИБКА] Файл dashboard.py не найден!
    pause
    exit /b
)

:: 5. ОБРАБОТКА ДАННЫХ [cite: 4]
if not exist %DATA_FILE% (
    echo [!] Файла данных нет. Запуск парсера...
    python hh_parser.py
) else (
    set /p refresh="Обновить данные с HH.ru? (y/n): "
)
if /i "%refresh%"=="y" python hh_parser.py

:: 6. ЗАПУСК ДАШБОРДА [cite: 5]
echo ----------------------------------------------------
echo [OK] Запуск визуализации...
echo Адрес: http://127.0.0.1:8050
echo ----------------------------------------------------
python dashboard.py

if %errorlevel% neq 0 (
    echo [ОШИБКА] Дашборд завершился со сбоем[cite: 5].
    pause
)
