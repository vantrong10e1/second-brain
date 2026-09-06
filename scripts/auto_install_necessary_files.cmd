@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Second Brain Installer

rem ============================================================
rem SECOND BRAIN - WINDOWS INSTALLER v7
rem Target: Windows 10 21H1+ x64 / Windows 11 x64
rem ============================================================

cd /d "%~dp0" >nul 2>&1
if errorlevel 1 goto :FAIL_START

set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%"
if exist "%SCRIPT_DIR%..\run-sb.cmd" set "PROJECT_DIR=%SCRIPT_DIR%.."
for %%I in ("%PROJECT_DIR%") do set "PROJECT_DIR=%%~fI"

set "LOG=%SCRIPT_DIR%install.log"
set "VENV=%PROJECT_DIR%\.venv"
set "PY=%VENV%\Scripts\python.exe"
set "PIP=%PY% -m pip"
set "PY312=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
set "PY_INSTALLER=%TEMP%\second_brain_python312.exe"
set "VC_INSTALLER=%TEMP%\second_brain_vc_x64.exe"
set "REQ=%TEMP%\second_brain_req_%RANDOM%.txt"
set "OLLAMA_EXE="
set "OLLAMA_MODEL=llama3.2"
set "OLLAMA_LEGACY_VERSION=0.5.7"
set "WIN_BUILD=0"
set "OLD_WIN=0"
set "MODEL_REQUIRED=0"
set "OLLAMA_REQUIRED=0"
set "FAILED=0"

set "TORCH_VERSION=2.7.1+cpu"
set "FAISS_VERSION=1.12.0"
set "ST_VERSION=5.1.1"
set "TRANSFORMERS_VERSION=4.57.1"
set "PYDANTIC_VERSION=2.10.6"

set "PY_URL=https://www.python.org/ftp/python/3.12.4/python-3.12.4-amd64.exe"
set "VC_URL=https://aka.ms/vs/17/release/vc_redist.x64.exe"
set "OLLAMA_URL=https://ollama.com/download/OllamaSetup.exe"
set "TORCH_INDEX=https://download.pytorch.org/whl/cpu"

>"%LOG%" echo ============================================================
>>"%LOG%" echo SECOND BRAIN INSTALLER v7
>>"%LOG%" echo Started %DATE% %TIME%
>>"%LOG%" echo SCRIPT_DIR=%SCRIPT_DIR%
>>"%LOG%" echo PROJECT_DIR=%PROJECT_DIR%
>>"%LOG%" echo ============================================================

call :HEADER "SECOND BRAIN INSTALLER v7"
echo Existing healthy components will be skipped.
echo Missing or broken components will be repaired.
echo Project environment: %VENV%
echo.

rem ------------------------------------------------------------
rem 0. Windows
rem ------------------------------------------------------------
call :STEP "0/8" "Checking Windows"
if /I not "%PROCESSOR_ARCHITECTURE%"=="AMD64" goto :FAIL_ARCH
call :GET_BUILD
if errorlevel 1 goto :FAIL_WINDOWS
echo Architecture: %PROCESSOR_ARCHITECTURE%
echo Windows build: %WIN_BUILD%
if %WIN_BUILD% LSS 19043 goto :FAIL_OLD_WINDOWS

if %WIN_BUILD% LSS 19045 (
    set "OLD_WIN=1"
    set "OLLAMA_REQUIRED=0"
    set "MODEL_REQUIRED=0"
    echo [INFO] Windows 10 21H1/21H2.
    echo [INFO] Python/RAG stack will be installed.
    echo [INFO] Ollama 0.5.7 will be attempted as compatibility runtime.
) else (
    set "OLD_WIN=0"
    set "OLLAMA_REQUIRED=1"
    set "MODEL_REQUIRED=1"
    echo [INFO] Windows 10 22H2+ / Windows 11.
    echo [INFO] Current Ollama + llama3.2 required.
)
echo OK.

rem ------------------------------------------------------------
rem 1. Python
rem ------------------------------------------------------------
call :STEP "1/8" "Checking Python 3.12"
call :FIND_PYTHON
if errorlevel 1 (
    echo [INSTALL] Python 3.12 not found.
    call :DOWNLOAD "%PY_URL%" "%PY_INSTALLER%" 1000000
    if errorlevel 1 goto :FAIL_PY_DOWNLOAD
    start /wait "" "%PY_INSTALLER%" /quiet InstallAllUsers=0 TargetDir="%LOCALAPPDATA%\Programs\Python\Python312" PrependPath=1 Include_launcher=1 Include_pip=1 Include_test=0
    set "RC=!errorlevel!"
    del /f /q "%PY_INSTALLER%" >nul 2>&1
    if not "!RC!"=="0" goto :FAIL_PY_INSTALL
    call :FIND_PYTHON
    if errorlevel 1 goto :FAIL_PY_MISSING
) else (
    echo [SKIP] Python 3.12: %BASE_PYTHON%
)
"%BASE_PYTHON%" -c "import sys; raise SystemExit(0 if sys.version_info[:2]==(3,12) else 1)" >nul 2>&1
if errorlevel 1 goto :FAIL_PY_VERSION
"%BASE_PYTHON%" -m ensurepip --upgrade >nul 2>&1
"%BASE_PYTHON%" -m pip --version >nul 2>&1
if errorlevel 1 goto :FAIL_PIP
echo Python OK.

rem ------------------------------------------------------------
rem 2. VC++ runtime
rem ------------------------------------------------------------
call :STEP "2/8" "Checking Microsoft VC++ x64 runtime"
call :CHECK_VC
if errorlevel 1 (
    echo [INSTALL] Microsoft VC++ x64 runtime.
    call :DOWNLOAD "%VC_URL%" "%VC_INSTALLER%" 1000000
    if errorlevel 1 goto :FAIL_VC_DOWNLOAD
    start /wait "" "%VC_INSTALLER%" /install /quiet /norestart
    set "RC=!errorlevel!"
    del /f /q "%VC_INSTALLER%" >nul 2>&1
    if not "!RC!"=="0" if not "!RC!"=="3010" goto :FAIL_VC
    call :CHECK_VC
    if errorlevel 1 goto :FAIL_VC
) else (
    echo [SKIP] Microsoft VC++ x64 runtime already installed.
)
echo OK.

rem ------------------------------------------------------------
rem 3. venv
rem ------------------------------------------------------------
call :STEP "3/8" "Creating/checking project virtual environment"
call :VENV_VALID
if errorlevel 1 (
    if exist "%VENV%" (
        echo [REPAIR] Existing .venv is invalid. Rebuilding it cleanly...
        rmdir /s /q "%VENV%" >nul 2>&1
        if exist "%VENV%" goto :FAIL_VENV_REMOVE
    ) else (
        echo [INSTALL] Creating project .venv...
    )
    "%BASE_PYTHON%" -m venv "%VENV%" >>"%LOG%" 2>&1
    if errorlevel 1 goto :FAIL_VENV
)
if not exist "%PY%" goto :FAIL_VENV
"%PY%" -m pip --version >nul 2>&1
if errorlevel 1 goto :FAIL_VENV_PIP
echo Virtual environment: %VENV%
echo OK.

rem ------------------------------------------------------------
rem 4. Python packages
rem ------------------------------------------------------------
call :STEP "4/8" "Installing/checking Python dependencies"

rem Only bootstrap pip when needed. Do not upgrade a healthy environment.
"%PY%" -m pip --version >nul 2>&1
if errorlevel 1 (
    "%PY%" -m ensurepip --upgrade >>"%LOG%" 2>&1
    if errorlevel 1 goto :FAIL_VENV_PIP
)

call :WRITE_REQ
if errorlevel 1 goto :FAIL_REQ

call :PY_STACK_HEALTHY
if errorlevel 1 (
    echo [INSTALL] Installing missing/incompatible Python packages...
    rem Install PyTorch separately from the official CPU index.
    "%PY%" -m pip install --disable-pip-version-check --no-cache-dir --force-reinstall --only-binary=:all: --index-url "%TORCH_INDEX%" "torch==%TORCH_VERSION%" >>"%LOG%" 2>&1
    if errorlevel 1 goto :FAIL_TORCH
    call :IMPORT_TORCH
    if errorlevel 1 goto :FAIL_TORCH

    rem All other packages come only from PyPI.
    "%PY%" -m pip install --disable-pip-version-check --no-cache-dir --prefer-binary -r "%REQ%" >>"%LOG%" 2>&1
    if errorlevel 1 goto :FAIL_PACKAGES
) else (
    echo [SKIP] Python dependency set is healthy.
)

call :VERIFY_IMPORTS
if errorlevel 1 goto :FAIL_IMPORTS

"%PY%" -m pip check >>"%LOG%" 2>&1
if errorlevel 1 (
    echo [REPAIR] Dependency graph inconsistent. Reinstalling the declared set...
    "%PY%" -m pip install --disable-pip-version-check --no-cache-dir --prefer-binary --upgrade-strategy only-if-needed -r "%REQ%" >>"%LOG%" 2>&1
    if errorlevel 1 goto :FAIL_PACKAGES
    "%PY%" -m pip check >>"%LOG%" 2>&1
    if errorlevel 1 goto :FAIL_PIP_CHECK
)
echo pip check: OK.
del /f /q "%REQ%" >nul 2>&1

rem ------------------------------------------------------------
rem 5. Ollama
rem ------------------------------------------------------------
call :STEP "5/8" "Checking Ollama"

if "%OLD_WIN%"=="1" (
    call :FIND_OLLAMA
    if errorlevel 1 (
        echo [INSTALL] Ollama %OLLAMA_LEGACY_VERSION% compatibility runtime.
        call :INSTALL_OLLAMA_LEGACY
        if errorlevel 1 (
            echo [WARN] Ollama 0.5.7 could not be installed on this old Windows build.
            echo [WARN] Python/RAG installation remains successful.
            set "OLLAMA_REQUIRED=0"
        ) else (
            call :FIND_OLLAMA
            if errorlevel 1 (
                echo [WARN] Ollama executable not found after installation.
                set "OLLAMA_REQUIRED=0"
            )
        )
    ) else (
        echo [SKIP] Ollama executable already exists.
    )
    if defined OLLAMA_EXE (
        "%OLLAMA_EXE%" --version >nul 2>&1
        if errorlevel 1 (
            echo [WARN] Ollama exists but cannot start on this OS.
            set "OLLAMA_REQUIRED=0"
        ) else (
            echo Ollama: OK.
        )
    )
) else (
    call :FIND_OLLAMA
    if errorlevel 1 (
        echo [INSTALL] Current Ollama.
        call :INSTALL_OLLAMA_LATEST
        if errorlevel 1 goto :FAIL_OLLAMA_INSTALL
        call :FIND_OLLAMA
        if errorlevel 1 goto :FAIL_OLLAMA_MISSING
    ) else (
        echo [SKIP] Ollama executable already installed.
    )
    "%OLLAMA_EXE%" --version >nul 2>&1
    if errorlevel 1 goto :FAIL_OLLAMA_RUN
    echo Ollama: OK.
)

rem ------------------------------------------------------------
rem 6. Ollama server/model
rem ------------------------------------------------------------
call :STEP "6/8" "Checking Ollama server/model"

if "%OLLAMA_REQUIRED%"=="1" (
    call :OLLAMA_READY
    if errorlevel 1 (
        echo [START] Starting Ollama...
        start "Second Brain Ollama" /b "%OLLAMA_EXE%" serve
        set "READY=0"
        for /l %%N in (1,1,30) do (
            if "!READY!"=="0" (
                timeout /t 2 /nobreak >nul
                call :OLLAMA_READY
                if not errorlevel 1 set "READY=1"
            )
        )
        if "!READY!"=="0" goto :FAIL_OLLAMA_SERVER
    ) else (
        echo [SKIP] Ollama server already ready.
    )

    if "%MODEL_REQUIRED%"=="1" (
        call :MODEL_EXISTS
        if errorlevel 1 (
            echo [INSTALL] Pulling %OLLAMA_MODEL%...
            "%OLLAMA_EXE%" pull "%OLLAMA_MODEL%" >>"%LOG%" 2>&1
            if errorlevel 1 goto :FAIL_MODEL
            call :MODEL_EXISTS
            if errorlevel 1 goto :FAIL_MODEL
        ) else (
            echo [SKIP] %OLLAMA_MODEL% already exists.
        )
        echo Model %OLLAMA_MODEL%: OK.
    )
) else (
    echo [SKIP] Model download on Windows 10 below 22H2.
)

rem ------------------------------------------------------------
rem 7. Final verification + launcher
rem ------------------------------------------------------------
call :STEP "7/8" "Final verification"

call :PY_STACK_HEALTHY
if errorlevel 1 goto :FAIL_FINAL
"%PY%" -m pip check >nul 2>&1
if errorlevel 1 goto :FAIL_FINAL

if "%OLLAMA_REQUIRED%"=="1" (
    if not defined OLLAMA_EXE goto :FAIL_FINAL
    call :OLLAMA_READY
    if errorlevel 1 goto :FAIL_FINAL
    call :MODEL_EXISTS
    if errorlevel 1 goto :FAIL_FINAL
)

set "RUN_SB=%SCRIPT_DIR%run-sb.cmd"
if not exist "%RUN_SB%" set "RUN_SB=%PROJECT_DIR%\run-sb.cmd"
if not exist "%RUN_SB%" goto :FAIL_RUN_SB

>>"%LOG%" echo SUCCESS %DATE% %TIME%
echo.
echo ============================================================
echo                  INSTALLATION COMPLETED
echo ============================================================
echo.
echo Launching:
echo %RUN_SB%
echo.

start "Second Brain" /d "%PROJECT_DIR%" cmd /k call "%RUN_SB%"
set "RC=!errorlevel!"
if not "!RC!"=="0" goto :FAIL_RUN_SB
exit /b 0

rem ============================================================
rem FUNCTIONS
rem ============================================================

:HEADER
echo.
echo ============================================================
echo                 %~1
echo ============================================================
echo.
exit /b 0

:STEP
echo.
echo ============================================================
echo [%~1] %~2
echo ============================================================
>>"%LOG%" echo [%~1] %~2
exit /b 0

:GET_BUILD
set "WIN_BUILD="
for /f "tokens=3" %%A in ('reg query "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion" /v CurrentBuildNumber 2^>nul ^| findstr /I "CurrentBuildNumber"') do set "WIN_BUILD=%%A"
if not defined WIN_BUILD exit /b 1
for /f "delims=0123456789" %%A in ("%WIN_BUILD%") do if not "%%A"=="" exit /b 1
set /a WIN_BUILD+=0
if %WIN_BUILD% LEQ 0 exit /b 1
exit /b 0

:FIND_PYTHON
set "BASE_PYTHON="
if exist "%PY312%" (
    "%PY312%" -c "import sys; raise SystemExit(0 if sys.version_info[:2]==(3,12) else 1)" >nul 2>&1
    if not errorlevel 1 set "BASE_PYTHON=%PY312%"
)
if defined BASE_PYTHON exit /b 0

where py.exe >nul 2>&1
if not errorlevel 1 (
    for /f "delims=" %%A in ('py -3.12 -c "import sys; print(sys.executable)" 2^>nul') do if exist "%%A" set "BASE_PYTHON=%%A"
)
if defined BASE_PYTHON exit /b 0

where python.exe >nul 2>&1
if not errorlevel 1 (
    for /f "delims=" %%A in ('python -c "import sys; print(sys.executable)" 2^>nul') do (
        if exist "%%A" (
            "%%A" -c "import sys; raise SystemExit(0 if sys.version_info[:2]==(3,12) else 1)" >nul 2>&1
            if not errorlevel 1 set "BASE_PYTHON=%%A"
        )
    )
)
if defined BASE_PYTHON exit /b 0
exit /b 1

:CHECK_VC
reg query "HKLM\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" /v Installed 2>nul | findstr /I /C:"0x1" >nul
if errorlevel 1 exit /b 1
exit /b 0

:VENV_VALID
if not exist "%PY%" exit /b 1
"%PY%" -c "import sys; raise SystemExit(0 if sys.version_info[:2]==(3,12) else 1)" >nul 2>&1
if errorlevel 1 exit /b 1
"%PY%" -m pip --version >nul 2>&1
if errorlevel 1 exit /b 1
exit /b 0

:WRITE_REQ
>"%REQ%" echo --index-url https://pypi.org/simple
>>"%REQ%" echo requests
>>"%REQ%" echo numpy==1.26.4
>>"%REQ%" echo tqdm
>>"%REQ%" echo colorama
>>"%REQ%" echo python-dotenv
>>"%REQ%" echo openai^<2
>>"%REQ%" echo tiktoken
>>"%REQ%" echo beautifulsoup4
>>"%REQ%" echo python-docx
>>"%REQ%" echo PyMuPDF
>>"%REQ%" echo openpyxl
>>"%REQ%" echo python-pptx
>>"%REQ%" echo faiss-cpu==%FAISS_VERSION%
>>"%REQ%" echo pydantic==%PYDANTIC_VERSION%
>>"%REQ%" echo transformers==%TRANSFORMERS_VERSION%
>>"%REQ%" echo sentence-transformers==%ST_VERSION%
>>"%REQ%" echo langchain==0.3.27
>>"%REQ%" echo langchain-core==0.3.80
>>"%REQ%" echo langchain-community==0.3.31
>>"%REQ%" echo langchain-text-splitters==0.3.11
>>"%REQ%" echo langchain-ollama==0.3.10
>>"%REQ%" echo langchain-openai==0.3.35
>>"%REQ%" echo ragas==0.3.9
>>"%REQ%" echo langfuse^>=3^,<4
if not exist "%REQ%" exit /b 1
exit /b 0

:PY_STACK_HEALTHY
call :VERIFY_IMPORTS
if errorlevel 1 exit /b 1
"%PY%" -m pip check >nul 2>&1
if errorlevel 1 exit /b 1
for /f "delims=" %%A in ('"%PY%" -c "import importlib.metadata as m; print(m.version('torch'))" 2^>nul') do set "INST_TORCH=%%A"
if /I not "!INST_TORCH!"=="%TORCH_VERSION%" exit /b 1
exit /b 0

:VERIFY_IMPORTS
"%PY%" -c "import requests,numpy,tqdm,colorama,dotenv,openai,tiktoken,bs4,docx,fitz,openpyxl,pptx,faiss,torch,transformers,sentence_transformers,pydantic,langchain,langchain_core,langchain_community,langchain_text_splitters,langchain_ollama,langchain_openai,ragas,langfuse; assert torch.__version__.startswith('2.7.1+cpu'); assert tuple(__import__('sys').version_info[:2])==(3,12)" >>"%LOG%" 2>&1
if errorlevel 1 (
    echo [ERROR] Python import validation failed. See install.log.
    "%PY%" -c "import sys; print(sys.version); print(sys.executable)"
    exit /b 1
)
exit /b 0

:IMPORT_TORCH
"%PY%" -c "import torch; print(torch.__version__); print(torch.__config__.show())" >>"%LOG%" 2>&1
if errorlevel 1 exit /b 1
exit /b 0

:FIND_OLLAMA
set "OLLAMA_EXE="
if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" set "OLLAMA_EXE=%LOCALAPPDATA%\Programs\Ollama\ollama.exe"
if not defined OLLAMA_EXE if exist "%LOCALAPPDATA%\Ollama\ollama.exe" set "OLLAMA_EXE=%LOCALAPPDATA%\Ollama\ollama.exe"
if not defined OLLAMA_EXE (
    where ollama.exe >nul 2>&1
    if not errorlevel 1 for /f "delims=" %%A in ('where ollama.exe 2^>nul') do if not defined OLLAMA_EXE set "OLLAMA_EXE=%%A"
)
if not defined OLLAMA_EXE exit /b 1
if not exist "%OLLAMA_EXE%" exit /b 1
"%OLLAMA_EXE%" --version >nul 2>&1
if errorlevel 1 exit /b 1
exit /b 0

:INSTALL_OLLAMA_LATEST
call :DOWNLOAD "%OLLAMA_URL%" "%TEMP%\SecondBrainOllamaSetup.exe" 1000000
if errorlevel 1 exit /b 1
start /wait "" "%TEMP%\SecondBrainOllamaSetup.exe" /silent
set "RC=!errorlevel!"
del /f /q "%TEMP%\SecondBrainOllamaSetup.exe" >nul 2>&1
if not "!RC!"=="0" exit /b 1
exit /b 0

:INSTALL_OLLAMA_LEGACY
set "PS=%TEMP%\second_brain_ollama_legacy.ps1"
>"%PS%" echo $ErrorActionPreference='Stop'
>>"%PS%" echo $env:OLLAMA_VERSION='%OLLAMA_LEGACY_VERSION%'
>>"%PS%" echo irm https://ollama.com/install.ps1 ^| iex
if not exist "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" exit /b 1
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%PS%" >>"%LOG%" 2>&1
set "RC=!errorlevel!"
del /f /q "%PS%" >nul 2>&1
if not "!RC!"=="0" exit /b 1
exit /b 0

:OLLAMA_READY
if not defined OLLAMA_EXE exit /b 1
"%OLLAMA_EXE%" list >nul 2>&1
exit /b %errorlevel%

:MODEL_EXISTS
if not defined OLLAMA_EXE exit /b 1
"%OLLAMA_EXE%" list 2>nul | findstr /I /B /C:"%OLLAMA_MODEL%" >nul
if errorlevel 1 exit /b 1
exit /b 0

:DOWNLOAD
set "URL=%~1"
set "OUT=%~2"
set "MIN=%~3"
if exist "%OUT%" del /f /q "%OUT%" >nul 2>&1
set "OK=0"

if exist "%SystemRoot%\System32\curl.exe" (
    "%SystemRoot%\System32\curl.exe" -L --fail --retry 4 --retry-delay 2 --connect-timeout 20 --max-time 1800 --silent --show-error "%URL%" -o "%OUT%" >>"%LOG%" 2>&1
    if exist "%OUT%" for %%F in ("%OUT%") do if %%~zF GTR %MIN% set "OK=1"
)
if "!OK!"=="0" if exist "%SystemRoot%\System32\certutil.exe" (
    del /f /q "%OUT%" >nul 2>&1
    "%SystemRoot%\System32\certutil.exe" -urlcache -split -f "%URL%" "%OUT%" >>"%LOG%" 2>&1
    if exist "%OUT%" for %%F in ("%OUT%") do if %%~zF GTR %MIN% set "OK=1"
)
if "!OK!"=="0" if exist "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" (
    del /f /q "%OUT%" >nul 2>&1
    "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue';Invoke-WebRequest -UseBasicParsing -Uri '%URL%' -OutFile '%OUT%'" >>"%LOG%" 2>&1
    if exist "%OUT%" for %%F in ("%OUT%") do if %%~zF GTR %MIN% set "OK=1"
)
if "!OK!"=="0" if defined BASE_PYTHON (
    del /f /q "%OUT%" >nul 2>&1
    "%BASE_PYTHON%" -c "import urllib.request; urllib.request.urlretrieve(r'%URL%',r'%OUT%')" >>"%LOG%" 2>&1
    if exist "%OUT%" for %%F in ("%OUT%") do if %%~zF GTR %MIN% set "OK=1"
)
if "!OK!"=="0" exit /b 1
exit /b 0

rem ============================================================
rem FAILURES - one exit path, never continue after failure
rem ============================================================

:FAIL_START
set "MSG=Cannot access installer directory."
goto :FAIL

:FAIL_ARCH
set "MSG=64-bit Windows (AMD64) is required."
goto :FAIL

:FAIL_WINDOWS
set "MSG=Cannot determine Windows build."
goto :FAIL

:FAIL_OLD_WINDOWS
set "MSG=Windows 10 21H1 (build 19043) or newer is required."
goto :FAIL

:FAIL_PY_DOWNLOAD
set "MSG=Could not download Python 3.12.4."
goto :FAIL

:FAIL_PY_INSTALL
set "MSG=Python 3.12 installation failed."
goto :FAIL

:FAIL_PY_MISSING
set "MSG=Python 3.12 was installed but could not be located."
goto :FAIL

:FAIL_PY_VERSION
set "MSG=Python 3.12 is required."
goto :FAIL

:FAIL_PIP
set "MSG=Base Python pip is unavailable."
goto :FAIL

:FAIL_VC_DOWNLOAD
set "MSG=Could not download Microsoft VC++ x64 runtime."
goto :FAIL

:FAIL_VC
set "MSG=Microsoft VC++ x64 runtime installation/verification failed."
goto :FAIL

:FAIL_VENV_REMOVE
set "MSG=Could not remove the broken .venv."
goto :FAIL

:FAIL_VENV
set "MSG=Could not create the project .venv."
goto :FAIL

:FAIL_VENV_PIP
set "MSG=Project .venv pip is unavailable."
goto :FAIL

:FAIL_REQ
set "MSG=Could not create dependency manifest."
goto :FAIL

:FAIL_TORCH
set "MSG=PyTorch CPU installation/import failed. See install.log."
goto :FAIL

:FAIL_PACKAGES
set "MSG=Python dependency installation failed. See install.log."
goto :FAIL

:FAIL_IMPORTS
set "MSG=One or more required Python imports failed. See install.log."
goto :FAIL

:FAIL_PIP_CHECK
set "MSG=pip check still reports dependency conflicts. See install.log."
goto :FAIL

:FAIL_OLLAMA_INSTALL
set "MSG=Ollama installation failed on Windows 10 22H2+/Windows 11."
goto :FAIL

:FAIL_OLLAMA_MISSING
set "MSG=Ollama executable was not found after installation."
goto :FAIL

:FAIL_OLLAMA_RUN
set "MSG=Ollama executable exists but cannot run."
goto :FAIL

:FAIL_OLLAMA_SERVER
set "MSG=Ollama server did not become ready."
goto :FAIL

:FAIL_MODEL
set "MSG=Ollama model llama3.2 could not be installed/verified."
goto :FAIL

:FAIL_RUN_SB
set "MSG=run-sb.cmd was not found."
goto :FAIL

:FAIL_FINAL
set "MSG=Final verification failed. See install.log."
goto :FAIL

:FAIL
set "FAILED=1"
echo.
echo ============================================================
echo                       INSTALL FAILED
echo ============================================================
echo.
echo %MSG%
echo.
echo Full log:
echo %LOG%
>>"%LOG%" echo FAILED %DATE% %TIME% - %MSG%
del /f /q "%REQ%" >nul 2>&1
echo.
echo Installer will close in 5 seconds.
timeout /t 5 /nobreak >nul
exit /b 1
