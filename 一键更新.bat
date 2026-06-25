@echo off
chcp 65001 >nul
echo.
echo ==========================================
echo    PDF简历 一键更新工具 (GitHub Pages)
echo    在线地址: https://runtimedaviddev.github.io/resume/
echo ==========================================
echo.

:: 切到工作目录
cd /d "D:\AI\PDFResume2HTML"

:: 使用 managed python，失败则用系统 python
set PYTHON=C:\Users\David\.workbuddy\binaries\python\versions\3.13.12\python.exe
if not exist "%PYTHON%" set PYTHON=python

:: ====== 第1步：生成 HTML ======
echo [1/3] 从 PDF 重新生成 HTML...
echo.
%PYTHON% generate_resume.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [错误] HTML生成失败，请检查 PDF2HTML.pdf 是否存在
    pause
    exit /b 1
)

:: ====== 第2步：复制为 index.html ======
echo.
echo [2/3] 复制为 index.html（短链接入口）...
copy /Y resume.html index.html >nul
echo 完成！

:: ====== 第3步：推送到 GitHub ======
echo.
echo [3/3] 推送至 GitHub Pages...
echo.
git add resume.html index.html
git commit -m "更新简历 %date% %time%" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 没有变更需要提交，直接推送...
)
git push origin main
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [错误] 推送失败，请检查网络和 GitHub 登录状态
    pause
    exit /b 1
)

echo.
echo ==========================================
echo   更新成功！等待约 1 分钟后访问：
echo   https://runtimedaviddev.github.io/resume/
echo ==========================================
pause
