@echo off
chcp 65001 >nul
title AI Assistant
echo ========================================
echo   AI 智能助手 正在启动...
echo   启动后会自动打开浏览器
echo   关闭此窗口即可停止服务
echo ========================================
echo.
cd /d "%~dp0"
python main.py
pause
