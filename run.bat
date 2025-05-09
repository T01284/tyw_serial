@echo off
setlocal enabledelayedexpansion

title Python�������Ͱ�װ

echo =================================================
echo               Python�������Ͱ�װ
echo =================================================
echo.
echo ���ڼ��ϵͳ����...
echo.

:: ��ʼ����־
set "install_python=1"
set "install_deps=0"

:: ���Python�Ƿ��Ѱ�װ����ȡ�汾
call :CheckPython
if !errorlevel! equ 0 (
    set "install_python=0"
)

:: ����Ƿ��Ѱ�װ����Ŀ�
if "!install_python!"=="0" (
    echo �������Python��...
    call :CheckDependencies
)

:: ��װPython�������Ҫ��
if "!install_python!"=="1" (
    call :InstallPython
    if !errorlevel! neq 0 (
        goto :Error
    )
    set "install_deps=1"
)

:: ��װ�����⣨�����Ҫ��
if "!install_deps!"=="1" (
    call :InstallDependencies
)

echo.
echo =================================================
echo              ����������ɣ�
echo       �����ڿ������д���ͨ�Ź��߳����ˡ�
echo =================================================
echo.
python tyw_serial.py
exit /b 0

:Error
echo.
echo ��װ����������������������������Ϣ��
pause
exit /b 1

:CheckPython
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo δ��⵽Python�������а�װ
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do (
    set "pyver=%%i"
)
echo ��⵽�Ѱ�װPython: !pyver!

:: ��ȡ�汾��
set "pyver=!pyver:Python =!"
for /f "tokens=1,2 delims=." %%a in ("!pyver!") do (
    set "pymajor=%%a"
    set "pyminor=%%b"
)

if !pymajor! EQU 3 (
    if !pyminor! GEQ 10 (
        echo ��ǰPython�汾����Ҫ�� ^(3.10����߰汾^)
        echo Python�������ͨ��
        exit /b 0
    ) else (
        echo ��ǰPython�汾���ͣ���Ҫ��װPython 3.10����߰汾
        exit /b 1
    )
) else (
    echo ��ǰPython�汾���ͣ���Ҫ��װPython 3.10����߰汾
    exit /b 1
)

:CheckDependencies
set "missing_deps=0"

:: ���PyQt5
echo ���PyQt5...
python -c "import PyQt5" >nul 2>&1
if %errorlevel% neq 0 (
    echo - δ��⵽PyQt5�⣬��Ҫ��װ
    set "install_deps=1"
    set "missing_deps=1"
) else (
    echo - PyQt5���Ѱ�װ
)

:: ���PySerial
echo ���PySerial...
python -c "import serial" >nul 2>&1
if %errorlevel% neq 0 (
    echo - δ��⵽PySerial�⣬��Ҫ��װ
    set "install_deps=1"
    set "missing_deps=1"
) else (
    echo - PySerial���Ѱ�װ
)

if "!missing_deps!"=="0" (
    echo ���������Python���Ѱ�װ
)
exit /b 0

:InstallPython
echo.
echo ���ڰ�װPython 3.10.11...
echo.

if not exist "python-3.10.11-amd64.exe" (
    echo �����Ҳ���Python��װ����
    echo ��ȷ��python-3.10.11-amd64.exe�ڵ�ǰĿ¼�¡�
    exit /b 1
)

echo ��ʼ��װPython���������Ҫ������...
start /wait python-3.10.11-amd64.exe /quiet TargetDir=D:\Python InstallAllUsers=1 PrependPath=1 Include_test=0

if not exist "D:\Python\python.exe" (
    echo ��װʧ�ܣ������Ƿ����㹻��Ȩ�޻��ֶ���װ��
    exit /b 1
)

echo Python��װ�ɹ���
exit /b 0

:InstallDependencies
echo.
echo ���ڰ�װ������...
echo.

echo 1. ����pip...
D:\Python\python.exe -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple >nul 2>&1
if %errorlevel% neq 0 (
    echo - ����pipʧ�ܣ�����������װ��������
) else (
    echo - pip���³ɹ�
)

echo 2. ��װPyQt5...
D:\Python\python.exe -m pip install PyQt5 -i https://pypi.tuna.tsinghua.edu.cn/simple >nul 2>&1
if %errorlevel% neq 0 (
    echo - ��װPyQt5ʧ�ܣ�
) else (
    echo - PyQt5��װ�ɹ�
)

echo 3. ��װPySerial...
D:\Python\python.exe -m pip install PySerial -i https://pypi.tuna.tsinghua.edu.cn/simple >nul 2>&1
if %errorlevel% neq 0 (
    echo - ��װPySerialʧ�ܣ�
) else (
    echo - PySerial��װ�ɹ�
)

echo �����ⰲװ��ɣ�
exit /b 0