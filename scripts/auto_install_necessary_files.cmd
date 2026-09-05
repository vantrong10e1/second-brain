@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM ============================================================
REM SECOND BRAIN - WINDOWS AUTO INSTALLER
REM Robust / idempotent / dependency-aware installer
REM ============================================================

cd /d "%~dp0"

title Second Brain - Auto Installer

set "LOG_FILE=%~dp0install.log"

REM ============================================================
REM CONFIGURATION
REM ============================================================

set "PYTHON_VERSION=3.12.4"
set "PYTHON_MAJOR_MINOR=3.12"
set "PYTHON_URL=https://www.python.org/ftp/python/3.12.4/python-3.12.4-amd64.exe"
set "PYTHON_INSTALLER=%TEMP%\second_brain_python_3.12.4.exe"
set "PYTHON_HOME=%LocalAppData%\Programs\Python\Python312"
set "PYTHON_EXE=%PYTHON_HOME%\python.exe"
set "PYTHON_SCRIPTS=%PYTHON_HOME%\Scripts"

REM Microsoft Visual C++ 2015-2022 x64 runtime.
set "VC_URL=https://aka.ms/vs/17/release/vc_redist.x64.exe"
set "VC_INSTALLER=%TEMP%\second_brain_vc_redist.x64.exe"

REM CPU-only PyTorch is intentional:
REM this avoids CUDA/native-wheel conflicts and is sufficient for the
REM current Sentence Transformers embedding pipeline.
set "TORCH_VERSION=2.7.1"
set "TORCH_INDEX=https://download.pytorch.org/whl/cpu"

set "OLLAMA_MODEL=llama3.2"
set "OLLAMA_URL=https://ollama.com/download/OllamaSetup.exe"
set "OLLAMA_INSTALLER=%TEMP%\second_brain_OllamaSetup.exe"
set "OLLAMA_EXE=%LocalAppData%\Programs\Ollama\ollama.exe"
set "OLLAMA_APP=%LocalAppData%\Programs\Ollama\ollama app.exe"

REM ============================================================
REM START / LOG
REM ============================================================

echo ============================================================ > "%LOG_FILE%"
echo SECOND BRAIN AUTO INSTALLER >> "%LOG_FILE%"
echo Started: %DATE% %TIME% >> "%LOG_FILE%"
echo ============================================================ >> "%LOG_FILE%"

call :header "SECOND BRAIN AUTO INSTALLER"

echo.
echo This installer prepares the complete Windows environment:
echo.
echo   Python %PYTHON_VERSION% x64
echo   pip
echo   Microsoft Visual C++ runtime
echo   PyTorch %TORCH_VERSION% CPU
echo   Sentence Transformers
echo   FAISS
echo   OpenAI / tiktoken
echo   LangChain 0.3.x stack
echo   Ragas 0.3.9
echo   Langfuse
echo   Document ingestion libraries
echo   Ollama
echo   llama3.2
echo.
echo A detailed log is written to:
echo %LOG_FILE%
echo.
echo ============================================================
echo.

REM ============================================================
REM [0/9] BASIC PLATFORM CHECK
REM ============================================================

call :step "0/9" "Checking Windows platform"

if /i not "%PROCESSOR_ARCHITECTURE%"=="AMD64" (
    call :fatal "This installer requires 64-bit Windows (AMD64)."
)

echo Windows architecture: %PROCESSOR_ARCHITECTURE%
echo OK.
echo.

REM ============================================================
REM [1/9] PYTHON
REM ============================================================

call :step "1/9" "Checking Python %PYTHON_VERSION%"

set "PYTHON_OK=0"
set "FOUND_PYTHON_EXE="

REM 1A. Python launcher.
where py.exe >nul 2>&1
if not errorlevel 1 (
    for /f "delims=" %%A in ('py -%PYTHON_MAJOR_MINOR% -c "import sys; print(sys.executable)" 2^>nul') do set "FOUND_PYTHON_EXE=%%A"

    if defined FOUND_PYTHON_EXE if exist "!FOUND_PYTHON_EXE!" (
        for /f "tokens=2" %%A in ('"!FOUND_PYTHON_EXE!" --version 2^>nul') do set "FOUND_PYTHON_VERSION=%%A"
        if "!FOUND_PYTHON_VERSION!"=="%PYTHON_VERSION%" (
            set "PYTHON_EXE=!FOUND_PYTHON_EXE!"
            set "PYTHON_HOME=!FOUND_PYTHON_EXE:\python.exe=!"
            set "PYTHON_SCRIPTS=!PYTHON_HOME!\Scripts"
            set "PYTHON_OK=1"
        )
    )
)

REM 1B. Standard per-user installation path.
if "!PYTHON_OK!"=="0" if exist "%PYTHON_EXE%" (
    for /f "tokens=2" %%A in ('"%PYTHON_EXE%" --version 2^>nul') do set "DIRECT_PYTHON_VERSION=%%A"
    if "!DIRECT_PYTHON_VERSION!"=="%PYTHON_VERSION%" set "PYTHON_OK=1"
)

if "!PYTHON_OK!"=="0" (
    echo Python %PYTHON_VERSION% was not found.
    echo Downloading official Python installer...
    call :download "%PYTHON_URL%" "%PYTHON_INSTALLER%" 1000000
    if errorlevel 1 call :fatal "Could not download Python %PYTHON_VERSION%."

    echo Installing Python %PYTHON_VERSION% for the current user...
    start /wait "" "%PYTHON_INSTALLER%" /quiet InstallAllUsers=0 TargetDir="%PYTHON_HOME%" PrependPath=1 Include_launcher=1 Include_pip=1 Include_test=0 SimpleInstall=0

    if errorlevel 1 call :fatal "Python installer returned an error."

    del /f /q "%PYTHON_INSTALLER%" >nul 2>&1

    REM Re-discover Python after installation.
    set "FOUND_PYTHON_EXE="

    if exist "%PYTHON_EXE%" set "FOUND_PYTHON_EXE=%PYTHON_EXE%"

    if not defined FOUND_PYTHON_EXE (
        where py.exe >nul 2>&1
        if not errorlevel 1 (
            for /f "delims=" %%A in ('py -%PYTHON_MAJOR_MINOR% -c "import sys; print(sys.executable)" 2^>nul') do set "FOUND_PYTHON_EXE=%%A"
        )
    )

    if not defined FOUND_PYTHON_EXE call :fatal "Python was installed but could not be located."

    set "PYTHON_EXE=!FOUND_PYTHON_EXE!"
    for %%A in ("!PYTHON_EXE!") do set "PYTHON_HOME=%%~dpA"
    if "!PYTHON_HOME:~-1!"=="\" set "PYTHON_HOME=!PYTHON_HOME:~0,-1!"
    set "PYTHON_SCRIPTS=!PYTHON_HOME!\Scripts"
)

REM Refresh PATH in this CMD process.
set "PATH=%PYTHON_HOME%;%PYTHON_SCRIPTS%;%PATH%"

for /f "tokens=2" %%A in ('"%PYTHON_EXE%" --version 2^>nul') do set "PYTHON_VERSION_CHECK=%%A"

if not "!PYTHON_VERSION_CHECK!"=="%PYTHON_VERSION%" (
    call :fatal "Wrong Python version. Required %PYTHON_VERSION%, found !PYTHON_VERSION_CHECK!."
)

echo Python: "%PYTHON_EXE%"
echo Version: %PYTHON_VERSION%
echo OK.
echo.

REM ============================================================
REM [2/9] PIP + VC RUNTIME
REM ============================================================

call :step "2/9" "Preparing pip and native Windows runtime"

"%PYTHON_EXE%" -m ensurepip --upgrade >> "%LOG_FILE%" 2>&1
if errorlevel 1 call :fatal "ensurepip failed."

"%PYTHON_EXE%" -m pip install --upgrade pip >> "%LOG_FILE%" 2>&1
if errorlevel 1 call :fatal "pip upgrade failed."

echo pip: OK

REM Check Microsoft VC++ x64 runtime.
set "VC_OK=0"

reg query "HKLM\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" /v Installed >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=3" %%A in ('reg query "HKLM\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" /v Installed 2^>nul ^| findstr /i "Installed"') do (
        if "%%A"=="0x1" set "VC_OK=1"
    )
)

if "!VC_OK!"=="0" (
    echo Microsoft Visual C++ x64 runtime not detected.
    echo Installing official runtime...
    call :download "%VC_URL%" "%VC_INSTALLER%" 1000000
    if errorlevel 1 call :fatal "Could not download Microsoft Visual C++ runtime."

    start /wait "" "%VC_INSTALLER%" /install /quiet /norestart
    set "VC_EXIT=!errorlevel!"
    del /f /q "%VC_INSTALLER%" >nul 2>&1

    if not "!VC_EXIT!"=="0" if not "!VC_EXIT!"=="3010" (
        echo WARNING: VC++ installer returned !VC_EXIT!.
        echo PyTorch validation below will determine whether native DLLs work.
    )
)

echo Native runtime preparation: OK.
echo.

REM ============================================================
REM [3/9] PYTORCH - EXPLICIT CPU WHEEL + HARD VALIDATION
REM ============================================================

call :step "3/9" "Installing and validating PyTorch"

set "TORCH_OK=0"

"%PYTHON_EXE%" -c "import torch; v=torch.__version__; print(v); raise SystemExit(0 if v.startswith('%TORCH_VERSION%') else 2)" > "%TEMP%\second_brain_torch_test.txt" 2>&1
if not errorlevel 1 set "TORCH_OK=1"

if "!TORCH_OK!"=="1" (
    echo Existing PyTorch %TORCH_VERSION% imports successfully.
    type "%TEMP%\second_brain_torch_test.txt"
) else (
    echo Existing PyTorch is broken or missing.
    echo Repairing with official CPU wheel...
    echo.

    "%PYTHON_EXE%" -m pip uninstall -y torch torchvision torchaudio >> "%LOG_FILE%" 2>&1

    "%PYTHON_EXE%" -m pip install --upgrade --force-reinstall "torch==%TORCH_VERSION%" --index-url "%TORCH_INDEX%" >> "%LOG_FILE%" 2>&1
    if errorlevel 1 (
        echo.
        echo PyTorch installation failed. Last pip output:
        type "%LOG_FILE%" | findstr /i /c:"ERROR" /c:"error" /c:"failed" /c:"Could not"
        call :fatal "PyTorch installation failed."
    )
)

del /f /q "%TEMP%\second_brain_torch_test.txt" >nul 2>&1

REM Hard import test. This catches WinError 126 / torch_cpu.dll failures.
"%PYTHON_EXE%" -c "import torch; x=torch.rand(2,2); print('torch:', torch.__version__); print('tensor:', x); print('cuda_available:', torch.cuda.is_available())"
if errorlevel 1 (
    echo.
    echo ============================================================
    echo PYTORCH NATIVE DLL VALIDATION FAILED
    echo ============================================================
    echo.
    echo This is usually a Windows native-runtime / DLL problem.
    echo The installer already attempted the Microsoft VC++ runtime.
    echo.
    echo See install.log for complete details.
    echo.
    call :fatal "PyTorch cannot be imported successfully."
)

echo PyTorch %TORCH_VERSION% CPU: OK.
echo.

REM ============================================================
REM [4/9] PYTHON PACKAGES
REM ============================================================

call :step "4/9" "Installing project Python dependencies"

REM Core / utilities
"%PYTHON_EXE%" -m pip install --upgrade ^
    requests ^
    numpy ^
    tqdm ^
    colorama ^
    python-dotenv ^
    openai ^
    tiktoken ^
    beautifulsoup4 ^
    python-docx ^
    PyMuPDF ^
    openpyxl ^
    python-pptx ^
    faiss-cpu ^
    pytest >> "%LOG_FILE%" 2>&1

if errorlevel 1 call :fatal "Core Python dependency installation failed."

REM NLP / embedding stack. PyTorch was installed first so pip cannot
REM silently replace the validated CPU build with an incompatible wheel.
"%PYTHON_EXE%" -m pip install --upgrade ^
    "sentence-transformers==5.2.3" ^
    spacy >> "%LOG_FILE%" 2>&1

if errorlevel 1 call :fatal "Embedding/NLP dependency installation failed."

REM LangChain stack intentionally remains on the 0.3.x generation used
REM by the current project.
"%PYTHON_EXE%" -m pip install --upgrade ^
    "langchain==0.3.27" ^
    "langchain-core==0.3.79" ^
    "langchain-community==0.3.31" ^
    "langchain-ollama==0.3.10" >> "%LOG_FILE%" 2>&1

if errorlevel 1 call :fatal "LangChain dependency installation failed."

REM Evaluation / observability.
"%PYTHON_EXE%" -m pip install --upgrade ^
    "ragas==0.3.9" ^
    langfuse >> "%LOG_FILE%" 2>&1

if errorlevel 1 call :fatal "Ragas/Langfuse installation failed."

echo Python packages installed.
echo.

REM ============================================================
REM [5/9] PACKAGE VALIDATION
REM ============================================================

call :step "5/9" "Validating Python packages"

call :python_test "import requests; print('requests OK')" "requests"
call :python_test "import numpy; print('numpy', numpy.__version__)" "numpy"
call :python_test "import tqdm; print('tqdm OK')" "tqdm"
call :python_test "import colorama; print('colorama OK')" "colorama"
call :python_test "import dotenv; print('python-dotenv OK')" "python-dotenv"
call :python_test "import openai; print('openai', openai.__version__)" "openai"
call :python_test "import tiktoken; print('tiktoken OK')" "tiktoken"
call :python_test "import bs4; print('beautifulsoup4 OK')" "beautifulsoup4"
call :python_test "import docx; print('python-docx OK')" "python-docx"
call :python_test "import fitz; print('PyMuPDF OK')" "PyMuPDF"
call :python_test "import openpyxl; print('openpyxl OK')" "openpyxl"
call :python_test "import pptx; print('python-pptx OK')" "python-pptx"
call :python_test "import faiss; print('faiss-cpu OK')" "faiss-cpu"
call :python_test "import spacy; print('spacy', spacy.__version__)" "spacy"

REM Most important native embedding validation.
call :python_test "import torch; print('torch', torch.__version__)" "torch"
call :python_test "from sentence_transformers import SentenceTransformer; print('sentence-transformers OK')" "sentence-transformers"

call :python_test "import langchain; print('langchain', langchain.__version__)" "langchain"
call :python_test "import langchain_core; print('langchain-core', langchain_core.__version__)" "langchain-core"
call :python_test "import langchain_community; print('langchain-community', langchain_community.__version__)" "langchain-community"
call :python_test "import langchain_ollama; print('langchain-ollama OK')" "langchain-ollama"

call :python_test "import ragas; print('ragas', ragas.__version__)" "ragas"
call :python_test "from ragas import evaluate; print('ragas.evaluate OK')" "ragas.evaluate"
call :python_test "import langfuse; print('langfuse OK')" "langfuse"

REM Dependency graph validation.
"%PYTHON_EXE%" -m pip check
if errorlevel 1 call :fatal "pip check failed. See the dependency conflict above and install.log."

echo.
echo All Python dependencies: OK.
echo.

REM ============================================================
REM [6/9] SENTENCE TRANSFORMERS REAL MODEL LOAD
REM ============================================================

call :step "6/9" "Validating Sentence Transformers runtime"

REM Do not download a Hugging Face model during installation.
REM Validate the library/native stack itself. The project's embedding
REM builder will download its configured model when first executed.
"%PYTHON_EXE%" -c "from sentence_transformers import SentenceTransformer; import torch; print('Sentence Transformers import: OK'); print('PyTorch:', torch.__version__); print('CUDA:', torch.cuda.is_available())"
if errorlevel 1 call :fatal "Sentence Transformers runtime validation failed."

echo Sentence Transformers runtime: OK.
echo.

REM ============================================================
REM [7/9] OLLAMA
REM ============================================================

call :step "7/9" "Installing and validating Ollama"

REM Official Ollama Windows docs currently require Windows 10 22H2+
REM for the native Windows application.
set "WIN_BUILD="

for /f "tokens=3" %%A in ('reg query "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion" /v CurrentBuildNumber 2^>nul ^| findstr /i "CurrentBuildNumber"') do set "WIN_BUILD=%%A"

if defined WIN_BUILD (
    echo Windows build: !WIN_BUILD!
    set /a WIN_BUILD_NUM=!WIN_BUILD! >nul 2>&1
    if !WIN_BUILD_NUM! LSS 19045 (
        echo.
        echo ============================================================
        echo ERROR: Windows is older than Windows 10 22H2.
        echo Ollama native Windows currently requires Windows 10 22H2+
        echo ============================================================
        echo.
        echo Upgrade Windows first, then rerun this installer.
        echo This is an operating-system requirement, not a Python issue.
        echo.
        call :fatal "Unsupported Windows version for Ollama."
    )
)

set "OLLAMA_FOUND=0"

if exist "%OLLAMA_EXE%" set "OLLAMA_FOUND=1"

if "!OLLAMA_FOUND!"=="0" (
    for /f "delims=" %%A in ('where ollama.exe 2^>nul') do (
        set "OLLAMA_EXE=%%A"
        set "OLLAMA_FOUND=1"
    )
)

if "!OLLAMA_FOUND!"=="0" (
    echo Ollama not found. Downloading official installer...
    call :download "%OLLAMA_URL%" "%OLLAMA_INSTALLER%" 1000000
    if errorlevel 1 call :fatal "Could not download Ollama."

    start /wait "" "%OLLAMA_INSTALLER%" /VERYSILENT /NORESTART /SUPPRESSMSGBOXES
    set "OLLAMA_INSTALL_EXIT=!errorlevel!"
    del /f /q "%OLLAMA_INSTALLER%" >nul 2>&1

    if not "!OLLAMA_INSTALL_EXIT!"=="0" call :fatal "Ollama installer returned !OLLAMA_INSTALL_EXIT!."

    if exist "%OLLAMA_EXE%" (
        set "OLLAMA_FOUND=1"
    ) else (
        for /f "delims=" %%A in ('where ollama.exe 2^>nul') do (
            set "OLLAMA_EXE=%%A"
            set "OLLAMA_FOUND=1"
        )
    )
)

if "!OLLAMA_FOUND!"=="0" call :fatal "Ollama executable was not found after installation."

set "PATH=%LocalAppData%\Programs\Ollama;%PATH%"

"%OLLAMA_EXE%" --version
if errorlevel 1 call :fatal "Ollama executable exists but cannot run."

echo Ollama executable: "%OLLAMA_EXE%"
echo Ollama: OK.
echo.

REM ============================================================
REM [8/9] OLLAMA SERVER + MODEL
REM ============================================================

call :step "8/9" "Starting Ollama and validating %OLLAMA_MODEL%"

REM First try the normal desktop application.
"%OLLAMA_EXE%" list >nul 2>&1

if errorlevel 1 (
    if exist "%OLLAMA_APP%" (
        echo Starting Ollama desktop application...
        start "" "%OLLAMA_APP%"
    )
)

REM Give the application/server time to initialize.
set "OLLAMA_READY=0"

for /l %%N in (1,1,12) do (
    if "!OLLAMA_READY!"=="0" (
        "%OLLAMA_EXE%" list >nul 2>&1
        if not errorlevel 1 set "OLLAMA_READY=1"
        if "!OLLAMA_READY!"=="0" timeout /t 2 /nobreak >nul
    )
)

REM If the desktop app did not expose the server, start the CLI server.
if "!OLLAMA_READY!"=="0" (
    echo Ollama desktop server was not ready. Starting "ollama serve"...
    start "" /b "%OLLAMA_EXE%" serve
    timeout /t 3 /nobreak >nul

    for /l %%N in (1,1,12) do (
        if "!OLLAMA_READY!"=="0" (
            "%OLLAMA_EXE%" list >nul 2>&1
            if not errorlevel 1 set "OLLAMA_READY=1"
            if "!OLLAMA_READY!"=="0" timeout /t 2 /nobreak >nul
        )
    )
)

if "!OLLAMA_READY!"=="0" call :fatal "Ollama server did not become ready."

echo Ollama server: OK.
echo.

"%OLLAMA_EXE%" list | findstr /i /r /c:"^%OLLAMA_MODEL%[ :]" >nul 2>&1

if errorlevel 1 (
    echo Model %OLLAMA_MODEL% is not installed.
    echo Pulling %OLLAMA_MODEL%...
    echo.
    "%OLLAMA_EXE%" pull "%OLLAMA_MODEL%"
    if errorlevel 1 call :fatal "Failed to download Ollama model %OLLAMA_MODEL%."
) else (
    echo Model %OLLAMA_MODEL% already installed.
)

"%OLLAMA_EXE%" list | findstr /i /r /c:"^%OLLAMA_MODEL%[ :]" >nul 2>&1
if errorlevel 1 call :fatal "Ollama model %OLLAMA_MODEL% was not found after pull."

echo Ollama model %OLLAMA_MODEL%: OK.
echo.

REM ============================================================
REM [9/9] FINAL END-TO-END VERIFICATION
REM ============================================================

call :step "9/9" "Final end-to-end verification"

echo.
echo ------------------------------------------------------------
echo Python
echo ------------------------------------------------------------
"%PYTHON_EXE%" --version
if errorlevel 1 call :fatal "Final Python verification failed."

echo.
echo ------------------------------------------------------------
echo pip
echo ------------------------------------------------------------
"%PYTHON_EXE%" -m pip --version
if errorlevel 1 call :fatal "Final pip verification failed."

echo.
echo ------------------------------------------------------------
echo PyTorch native import
echo ------------------------------------------------------------
"%PYTHON_EXE%" -c "import torch; print('PyTorch:', torch.__version__); print('CUDA available:', torch.cuda.is_available())"
if errorlevel 1 call :fatal "Final PyTorch verification failed."

echo.
echo ------------------------------------------------------------
echo Sentence Transformers
echo ------------------------------------------------------------
"%PYTHON_EXE%" -c "from sentence_transformers import SentenceTransformer; print('Sentence Transformers: OK')"
if errorlevel 1 call :fatal "Final Sentence Transformers verification failed."

echo.
echo ------------------------------------------------------------
echo FAISS
echo ------------------------------------------------------------
"%PYTHON_EXE%" -c "import faiss; print('FAISS:', faiss.__version__ if hasattr(faiss, '__version__') else 'OK')"
if errorlevel 1 call :fatal "Final FAISS verification failed."

echo.
echo ------------------------------------------------------------
echo Ragas
echo ------------------------------------------------------------
"%PYTHON_EXE%" -c "import ragas; print('Ragas:', ragas.__version__)"
if errorlevel 1 call :fatal "Final Ragas verification failed."

echo.
echo ------------------------------------------------------------
echo LangChain
echo ------------------------------------------------------------
"%PYTHON_EXE%" -c "import langchain, langchain_core, langchain_community, langchain_ollama; print('LangChain:', langchain.__version__); print('LangChain Core:', langchain_core.__version__); print('LangChain Community:', langchain_community.__version__); print('LangChain Ollama: OK')"
if errorlevel 1 call :fatal "Final LangChain verification failed."

echo.
echo ------------------------------------------------------------
echo Langfuse
echo ------------------------------------------------------------
"%PYTHON_EXE%" -c "from langfuse import get_client; print('Langfuse: OK')"
if errorlevel 1 call :fatal "Final Langfuse verification failed."

echo.
echo ------------------------------------------------------------
echo Ollama
echo ------------------------------------------------------------
"%OLLAMA_EXE%" --version
if errorlevel 1 call :fatal "Final Ollama executable verification failed."

echo.
echo ------------------------------------------------------------
echo Ollama models
echo ------------------------------------------------------------
"%OLLAMA_EXE%" list
if errorlevel 1 call :fatal "Final Ollama server/model verification failed."

echo.
echo ------------------------------------------------------------
echo pip check
echo ------------------------------------------------------------
"%PYTHON_EXE%" -m pip check
if errorlevel 1 call :fatal "Final pip check failed."

echo.
echo ============================================================
echo              INSTALLATION COMPLETED
echo ============================================================
echo.
echo Python:
"%PYTHON_EXE%" --version
echo.
echo PyTorch:
"%PYTHON_EXE%" -c "import torch; print(torch.__version__)"
echo.
echo Ragas:
"%PYTHON_EXE%" -c "import ragas; print(ragas.__version__)"
echo.
echo Ollama:
"%OLLAMA_EXE%" --version
echo.
echo Model:
echo %OLLAMA_MODEL%
echo.
echo Log:
echo %LOG_FILE%
echo.
echo The Second Brain Python environment is ready.
echo ============================================================
echo.

echo SUCCESS %DATE% %TIME% >> "%LOG_FILE%"

pause
exit /b 0


REM ============================================================
REM SUBROUTINES
REM ============================================================

:header
echo.
echo ============================================================
echo              %~1
echo ============================================================
echo.
exit /b 0


:step
echo.
echo ============================================================
echo [%~1] %~2
echo ============================================================
echo [%~1] %~2 >> "%LOG_FILE%"
echo.
exit /b 0


:python_test
"%PYTHON_EXE%" -c "%~1"
if errorlevel 1 (
    echo.
    echo ERROR validating: %~2
    echo See install.log for details.
    call :fatal "Python package validation failed: %~2"
)
exit /b 0


:download
REM Usage:
REM call :download "URL" "OUTPUT_FILE" MIN_BYTES
set "DL_URL=%~1"
set "DL_FILE=%~2"
set "DL_MIN=%~3"

if exist "%DL_FILE%" del /f /q "%DL_FILE%" >nul 2>&1

echo Downloading:
echo   %DL_URL%
echo To:
echo   %DL_FILE%

set "DL_OK=0"

REM 1. Windows curl.exe
if exist "%SystemRoot%\System32\curl.exe" (
    echo [download 1/4] curl.exe
    "%SystemRoot%\System32\curl.exe" -L --fail --retry 4 --retry-delay 2 --connect-timeout 20 --max-time 1800 --silent --show-error "%DL_URL%" -o "%DL_FILE%" >> "%LOG_FILE%" 2>&1
    if exist "%DL_FILE%" for %%F in ("%DL_FILE%") do if %%~zF GTR %DL_MIN% set "DL_OK=1"
)

REM 2. certutil.exe
if "!DL_OK!"=="0" (
    if exist "%DL_FILE%" del /f /q "%DL_FILE%" >nul 2>&1
    if exist "%SystemRoot%\System32\certutil.exe" (
        echo [download 2/4] certutil.exe
        "%SystemRoot%\System32\certutil.exe" -urlcache -split -f "%DL_URL%" "%DL_FILE%" >> "%LOG_FILE%" 2>&1
        if exist "%DL_FILE%" for %%F in ("%DL_FILE%") do if %%~zF GTR %DL_MIN% set "DL_OK=1"
    )
)

REM 3. Absolute-path Windows PowerShell
if "!DL_OK!"=="0" (
    if exist "%DL_FILE%" del /f /q "%DL_FILE%" >nul 2>&1
    if exist "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" (
        echo [download 3/4] Windows PowerShell
        "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $ProgressPreference='SilentlyContinue'; Invoke-WebRequest -UseBasicParsing -Uri '%DL_URL%' -OutFile '%DL_FILE%'" >> "%LOG_FILE%" 2>&1
        if exist "%DL_FILE%" for %%F in ("%DL_FILE%") do if %%~zF GTR %DL_MIN% set "DL_OK=1"
    )
)

REM 4. Existing Python launcher
if "!DL_OK!"=="0" (
    if exist "%DL_FILE%" del /f /q "%DL_FILE%" >nul 2>&1
    where py.exe >nul 2>&1
    if not errorlevel 1 (
        echo [download 4/4] Python urllib
        py -3 -c "import urllib.request; urllib.request.urlretrieve(r'%DL_URL%', r'%DL_FILE%')" >> "%LOG_FILE%" 2>&1
        if exist "%DL_FILE%" for %%F in ("%DL_FILE%") do if %%~zF GTR %DL_MIN% set "DL_OK=1"
    )
)

if "!DL_OK!"=="0" (
    echo Download failed.
    exit /b 1
)

for %%F in ("%DL_FILE%") do echo Downloaded %%~zF bytes.
exit /b 0


:fatal
set "FATAL_MESSAGE=%~1"
goto INSTALLER_FATAL


:INSTALLER_FATAL
echo.
echo ============================================================
echo ERROR
echo ============================================================
echo %FATAL_MESSAGE%
echo.
echo A complete log is available at:
echo %LOG_FILE%
echo.
echo Installer stopped safely.
echo ============================================================
echo FAILURE %DATE% %TIME% - %FATAL_MESSAGE% >> "%LOG_FILE%"
echo.
pause
exit /b 1
