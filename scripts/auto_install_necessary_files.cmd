@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0"

title Second Brain - Auto Installer

REM ============================================================
REM CONFIG
REM ============================================================

set "PYTHON_VERSION=3.12.4"
set "PYTHON_URL=https://www.python.org/ftp/python/3.12.4/python-3.12.4-amd64.exe"
set "PYTHON_INSTALLER=%TEMP%\python-3.12.4-amd64.exe"

set "OLLAMA_MODEL=llama3.2"


REM ============================================================
REM START
REM ============================================================

echo.
echo ============================================================
echo              SECOND BRAIN AUTO INSTALLER
echo ============================================================
echo.
echo This installer will setup:
echo.
echo   Python 3.12.4
echo   pip
echo   RAG dependencies
echo   Ragas 0.3.9
echo   Langfuse
echo   Ollama
echo   llama3.2
echo.
echo ============================================================
echo.


REM ============================================================
REM 1. CHECK PYTHON 3.12.4
REM ============================================================

echo [1/9] Checking Python %PYTHON_VERSION%...
echo.

set "PYTHON_OK=0"

py -3.12 --version >nul 2>&1

if not errorlevel 1 (

    for /f "tokens=2" %%A in ('py -3.12 --version 2^>nul') do (
        set "CURRENT_PYTHON=%%A"
    )

    if "!CURRENT_PYTHON!"=="%PYTHON_VERSION%" (
        set "PYTHON_OK=1"
        echo Python %PYTHON_VERSION% is already installed.
    ) else (
        echo Found Python !CURRENT_PYTHON!
        echo Required Python %PYTHON_VERSION%.
    )
)


REM ============================================================
REM 2. DOWNLOAD + INSTALL PYTHON
REM ============================================================

if "%PYTHON_OK%"=="0" (

    echo.
    echo Python %PYTHON_VERSION% is required.
    echo Downloading official Python installer...
    echo.

    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_INSTALLER%'"

    if errorlevel 1 (
        echo.
        echo ERROR: Failed to download Python %PYTHON_VERSION%.
        echo.
        pause
        exit /b 1
    )

    echo.
    echo Python installer downloaded.
    echo.
    echo Installing Python %PYTHON_VERSION%...
    echo.

    "%PYTHON_INSTALLER%" ^
        /quiet ^
        InstallAllUsers=0 ^
        PrependPath=1 ^
        Include_test=0 ^
        Include_launcher=1

    if errorlevel 1 (
        echo.
        echo ERROR: Python installation failed.
        echo.
        pause
        exit /b 1
    )

    echo.
    echo Python installation completed.
    echo.

    del /q "%PYTHON_INSTALLER%" >nul 2>&1

    REM Refresh PATH for current script
    set "PATH=%LocalAppData%\Programs\Python\Python312;%LocalAppData%\Programs\Python\Python312\Scripts;%PATH%"
)


REM ============================================================
REM 3. VERIFY PYTHON
REM ============================================================

echo [2/9] Verifying Python...
echo.

py -3.12 --version

if errorlevel 1 (
    echo.
    echo ERROR: Python 3.12 cannot be found.
    echo.
    echo Please restart Windows and run this installer again.
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%A in ('py -3.12 --version') do (
    set "PYTHON_VERSION_CHECK=%%A"
)

if not "!PYTHON_VERSION_CHECK!"=="3.12.4" (
    echo.
    echo ERROR: Wrong Python version detected:
    echo !PYTHON_VERSION_CHECK!
    echo.
    echo Required:
    echo 3.12.4
    echo.
    pause
    exit /b 1
)

echo Python 3.12.4: OK
echo.


REM ============================================================
REM 4. UPGRADE PIP
REM ============================================================

echo [3/9] Updating pip...
echo.

py -3.12 -m pip install --upgrade pip

if errorlevel 1 (
    echo.
    echo ERROR: Failed to update pip.
    echo.
    pause
    exit /b 1
)

echo.
echo pip: OK
echo.


REM ============================================================
REM 5. INSTALL PYTHON PACKAGES
REM ============================================================

echo [4/9] Installing Python packages...
echo.
echo This may take several minutes.
echo.

py -3.12 -m pip install ^
    requests ^
    numpy ^
    tqdm ^
    colorama ^
    python-dotenv ^
    sentence-transformers ^
    langfuse ^
    "ragas==0.3.9" ^
    langchain ^
    langchain-core ^
    "langchain-community==0.3.31" ^
    langchain-ollama

if errorlevel 1 (
    echo.
    echo ERROR: Failed to install Python packages.
    echo.
    pause
    exit /b 1
)

echo.
echo Python packages installed successfully.
echo.


REM ============================================================
REM 6. VERIFY PYTHON PACKAGES
REM ============================================================

echo [5/9] Verifying Python packages...
echo.

py -3.12 -c "import requests; print('[OK] requests')"

if errorlevel 1 goto PACKAGE_ERROR

py -3.12 -c "import numpy; print('[OK] numpy')"

if errorlevel 1 goto PACKAGE_ERROR

py -3.12 -c "import tqdm; print('[OK] tqdm')"

if errorlevel 1 goto PACKAGE_ERROR

py -3.12 -c "import colorama; print('[OK] colorama')"

if errorlevel 1 goto PACKAGE_ERROR

py -3.12 -c "import dotenv; print('[OK] python-dotenv')"

if errorlevel 1 goto PACKAGE_ERROR

py -3.12 -c "import sentence_transformers; print('[OK] sentence-transformers')"

if errorlevel 1 goto PACKAGE_ERROR

py -3.12 -c "import langfuse; print('[OK] langfuse')"

if errorlevel 1 goto PACKAGE_ERROR

py -3.12 -c "import ragas; print('[OK] ragas 0.3.9')"

if errorlevel 1 goto PACKAGE_ERROR

py -3.12 -c "from ragas import evaluate; print('[OK] ragas evaluate')"

if errorlevel 1 goto PACKAGE_ERROR

py -3.12 -c "import langchain; print('[OK] langchain')"

if errorlevel 1 goto PACKAGE_ERROR

py -3.12 -c "import langchain_core; print('[OK] langchain-core')"

if errorlevel 1 goto PACKAGE_ERROR

py -3.12 -c "import langchain_community; print('[OK] langchain-community')"

if errorlevel 1 goto PACKAGE_ERROR

py -3.12 -c "import langchain_ollama; print('[OK] langchain-ollama')"

if errorlevel 1 goto PACKAGE_ERROR

echo.
echo All Python packages: OK
echo.

goto OLLAMA


:PACKAGE_ERROR

echo.
echo ============================================================
echo ERROR: One or more Python packages failed.
echo ============================================================
echo.
pause
exit /b 1


REM ============================================================
REM 7. INSTALL OLLAMA
REM ============================================================

:OLLAMA

echo [6/9] Checking Ollama...
echo.

where ollama >nul 2>&1

if errorlevel 1 (

    echo Ollama was not found.
    echo.
    echo Installing Ollama...
    echo.

    winget install --id Ollama.Ollama --exact

    if errorlevel 1 (
        echo.
        echo ERROR: Failed to install Ollama.
        echo.
        pause
        exit /b 1
    )

    echo.
    echo Ollama installation completed.
    echo.

    REM Refresh PATH
    call refreshenv >nul 2>&1
)

where ollama >nul 2>&1

if errorlevel 1 (

    echo.
    echo ============================================================
    echo Ollama was installed but is not available in this terminal.
    echo ============================================================
    echo.
    echo Please close this window and run the installer again.
    echo.
    pause
    exit /b 1
)

ollama --version

echo.
echo Ollama: OK
echo.


REM ============================================================
REM 8. INSTALL LLAMA3.2
REM ============================================================

echo [7/9] Checking Ollama model: %OLLAMA_MODEL%
echo.

ollama list | findstr /i "%OLLAMA_MODEL%" >nul 2>&1

if errorlevel 1 (

    echo %OLLAMA_MODEL% was not found.
    echo.
    echo Downloading %OLLAMA_MODEL%...
    echo.

    ollama pull %OLLAMA_MODEL%

    if errorlevel 1 (
        echo.
        echo ERROR: Failed to download %OLLAMA_MODEL%.
        echo.
        pause
        exit /b 1
    )

) else (

    echo %OLLAMA_MODEL% is already installed.

)

echo.
echo Ollama model: OK
echo.


REM ============================================================
REM 9. FINAL VERIFICATION
REM ============================================================

echo [8/9] Final verification...
echo.

echo ------------------------------------------------------------
echo Python
echo ------------------------------------------------------------

py -3.12 --version

echo.

echo ------------------------------------------------------------
echo Pip
echo ------------------------------------------------------------

py -3.12 -m pip --version

echo.

echo ------------------------------------------------------------
echo Ollama
echo ------------------------------------------------------------

ollama --version

echo.

echo ------------------------------------------------------------
echo Ollama Models
echo ------------------------------------------------------------

ollama list

echo.

echo ------------------------------------------------------------
echo Ragas
echo ------------------------------------------------------------

py -3.12 -c "import ragas; print('Ragas version:', ragas.__version__)"

echo.

echo ------------------------------------------------------------
echo LangChain Community
echo ------------------------------------------------------------

py -3.12 -c "import langchain_community; print('langchain-community:', langchain_community.__version__)"

echo.

echo ------------------------------------------------------------
echo Sentence Transformers
echo ------------------------------------------------------------

py -3.12 -c "from sentence_transformers import SentenceTransformer; print('sentence-transformers: OK')"

echo.


REM ============================================================
REM FINISH
REM ============================================================

echo [9/9] Installation completed.
echo.

echo ============================================================
echo              INSTALLATION COMPLETED
echo ============================================================
echo.
echo Python:
py -3.12 --version

echo.
echo Ollama:
ollama --version

echo.
echo Model:
echo %OLLAMA_MODEL%

echo.
echo Ragas:
py -3.12 -c "import ragas; print(ragas.__version__)"

echo.
echo Your Second Brain environment is ready.
echo.
echo ============================================================
echo.

pause
exit /b 0