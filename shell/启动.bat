@echo off
chcp 65001 >nul
cd /d "%~dp0"
title ChatGuard 本地服务

where py >nul 2>nul && set "PY=py -3" && goto run
where python >nul 2>nul && set "PY=python" && goto run
goto nopython

:run
echo 正在启动 ChatGuard，浏览器会自动打开...
echo.
%PY% api.py --open
goto end

:nopython
echo.
echo  [!] 没有找到 Python。
echo      请先安装 Python 3.7+ : https://www.python.org/downloads/
echo      安装时务必勾选 "Add Python to PATH"
echo.
pause
exit /b 1

:end
echo.
pause
