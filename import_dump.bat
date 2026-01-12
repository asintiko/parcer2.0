@echo off
echo =====================================================
echo Импорт дампа базы данных receipt_parser_dump.sql
echo =====================================================
echo.
echo Этот скрипт создаст базу данных и импортирует дамп.
echo Вам потребуется ввести пароль PostgreSQL.
echo.
pause

REM Создание базы данных (если не существует)
echo Создание базы данных receipt_parser_db...
psql -U postgres -c "DROP DATABASE IF EXISTS receipt_parser_db;"
psql -U postgres -c "CREATE DATABASE receipt_parser_db;"

echo.
echo Импорт дампа в базу данных...
psql -U postgres -d receipt_parser_db -f receipt_parser_dump.sql

echo.
echo =====================================================
echo Импорт завершен!
echo =====================================================
echo.
echo Проверка количества записей в таблице checks:
psql -U postgres -d receipt_parser_db -c "SELECT COUNT(*) as total_records FROM checks;"

echo.
pause
