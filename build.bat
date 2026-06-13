@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ========================================
echo   音频波形可视化器 - PyInstaller 打包
echo ========================================
echo.

call .venv\Scripts\activate

if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

echo [1/2] 正在打包...
pyinstaller ^
    --noconsole ^
    --onefile ^
    --name "AudioVisualizer" ^
    --hidden-import=soundcard._soundcard ^
    --hidden-import=soundcard.mediafoundation ^
    --hidden-import=numpy.core ^
    --hidden-import=PyQt5.sip ^
    --collect-binaries=soundcard ^
    --clean ^
    main.py

if %ERRORLEVEL% NEQ 0 (
    echo [错误] 打包失败！
    pause
    exit /b 1
)

echo.
echo [2/2] 完成！
echo 可执行文件: dist\AudioVisualizer.exe
echo.
pause

