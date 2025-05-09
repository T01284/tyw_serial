@echo off
setlocal enabledelayedexpansion

title Python环境检查和安装

echo =================================================
echo               Python环境检查和安装
echo =================================================
echo.
echo 正在检查系统环境...
echo.

:: 初始化标志
set "install_python=1"
set "install_deps=0"

:: 检查Python是否已安装并获取版本
call :CheckPython
if !errorlevel! equ 0 (
    set "install_python=0"
)

:: 检查是否已安装所需的库
if "!install_python!"=="0" (
    echo 检查所需Python库...
    call :CheckDependencies
)

:: 安装Python（如果需要）
if "!install_python!"=="1" (
    call :InstallPython
    if !errorlevel! neq 0 (
        goto :Error
    )
    set "install_deps=1"
)

:: 安装依赖库（如果需要）
if "!install_deps!"=="1" (
    call :InstallDependencies
)

echo.
echo =================================================
echo              环境配置完成！
echo       您现在可以运行串口通信工具程序了。
echo =================================================
echo.
python tyw_serial.py
exit /b 0

:Error
echo.
echo 安装过程中遇到错误，请检查上述错误信息。
pause
exit /b 1

:CheckPython
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 未检测到Python，将进行安装
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do (
    set "pyver=%%i"
)
echo 检测到已安装Python: !pyver!

:: 提取版本号
set "pyver=!pyver:Python =!"
for /f "tokens=1,2 delims=." %%a in ("!pyver!") do (
    set "pymajor=%%a"
    set "pyminor=%%b"
)

if !pymajor! EQU 3 (
    if !pyminor! GEQ 10 (
        echo 当前Python版本满足要求 ^(3.10或更高版本^)
        echo Python环境检查通过
        exit /b 0
    ) else (
        echo 当前Python版本过低，需要安装Python 3.10或更高版本
        exit /b 1
    )
) else (
    echo 当前Python版本过低，需要安装Python 3.10或更高版本
    exit /b 1
)

:CheckDependencies
set "missing_deps=0"

:: 检查PyQt5
echo 检查PyQt5...
python -c "import PyQt5" >nul 2>&1
if %errorlevel% neq 0 (
    echo - 未检测到PyQt5库，需要安装
    set "install_deps=1"
    set "missing_deps=1"
) else (
    echo - PyQt5库已安装
)

:: 检查PySerial
echo 检查PySerial...
python -c "import serial" >nul 2>&1
if %errorlevel% neq 0 (
    echo - 未检测到PySerial库，需要安装
    set "install_deps=1"
    set "missing_deps=1"
) else (
    echo - PySerial库已安装
)

if "!missing_deps!"=="0" (
    echo 所有所需的Python库已安装
)
exit /b 0

:InstallPython
echo.
echo 正在安装Python 3.10.11...
echo.

if not exist "python-3.10.11-amd64.exe" (
    echo 错误：找不到Python安装程序。
    echo 请确保python-3.10.11-amd64.exe在当前目录下。
    exit /b 1
)

echo 开始安装Python，这可能需要几分钟...
start /wait python-3.10.11-amd64.exe /quiet TargetDir=D:\Python InstallAllUsers=1 PrependPath=1 Include_test=0

if not exist "D:\Python\python.exe" (
    echo 安装失败！请检查是否有足够的权限或手动安装。
    exit /b 1
)

echo Python安装成功！
exit /b 0

:InstallDependencies
echo.
echo 正在安装依赖库...
echo.

echo 1. 更新pip...
D:\Python\python.exe -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple >nul 2>&1
if %errorlevel% neq 0 (
    echo - 更新pip失败，但将继续安装其他依赖
) else (
    echo - pip更新成功
)

echo 2. 安装PyQt5...
D:\Python\python.exe -m pip install PyQt5 -i https://pypi.tuna.tsinghua.edu.cn/simple >nul 2>&1
if %errorlevel% neq 0 (
    echo - 安装PyQt5失败！
) else (
    echo - PyQt5安装成功
)

echo 3. 安装PySerial...
D:\Python\python.exe -m pip install PySerial -i https://pypi.tuna.tsinghua.edu.cn/simple >nul 2>&1
if %errorlevel% neq 0 (
    echo - 安装PySerial失败！
) else (
    echo - PySerial安装成功
)

echo 依赖库安装完成！
exit /b 0