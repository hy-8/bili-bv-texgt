@echo off
chcp 65001 >nul 2>&1
title bili2text-new
cd /d "%~dp0"

echo ========================================
echo   bili2text-new - B站视频文案提取工具
echo ========================================
echo.

REM 检查虚拟环境
if not exist ".env\Scripts\python.exe" (
    echo [错误] 未找到虚拟环境，请先运行以下命令创建：
    echo   python -m venv .env
    echo   .env\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

REM 启动交互模式
.env\Scripts\python.exe main.py %*

if errorlevel 1 (
    echo.
    echo [提示] 程序运行出错
)

echo.
pause
