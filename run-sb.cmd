@echo off
setlocal

cd /d "%~dp0"

:MENU

cls

echo.
echo Chon chuc nang su dung:
echo.
echo 1. Install necessary files
echo 2. Ingest documents
echo 3. Maintain system
echo 4. Run RAG
echo 5. Exit
echo.

set /p choice="Ban hay lua chon: "


if "%choice%"=="1" goto INSTALL
if "%choice%"=="2" goto INGEST
if "%choice%"=="3" goto MAINTAIN
if "%choice%"=="4" goto RAG
if "%choice%"=="5" goto EXIT


echo.
echo Lua chon khong hop le.
echo.
pause

goto MENU


:INSTALL

cls

echo.
echo INSTALL NECESSARY FILES
echo.

call "%~dp0scripts\auto_install_necessary_files.cmd"

echo.
echo INSTALLATION FINISHED
echo.

pause

goto MENU


:INGEST

cls

echo.
echo INGEST DOCUMENTS
echo.

py -3.12 "%~dp0scripts\ingest_all.py"

echo.
echo INGEST FINISHED
echo.

pause

goto MENU


:MAINTAIN

cls

echo.
echo MAINTAIN SYSTEM
echo.

py -3.12 "%~dp0scripts\maintain_system.py"

echo.
echo MAINTAIN FINISHED
echo.

pause

goto MENU


:RAG

cls

echo.
echo RUN RAG
echo.

py -3.12 "%~dp0engine\rag.py"

echo.
echo RAG FINISHED
echo.

pause

goto MENU


:EXIT

cls

echo.
echo Goodbye.
echo.

endlocal
exit /b 0