@echo off
chcp 65001 >nul
title PyInstaller 智能打包脚本

echo 🔧 PyInstaller 智能打包脚本
echo ============================================================

REM 检查Python环境
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未找到Python环境
    echo 请确保Python已正确安装并添加到PATH
    pause
    exit /b 1
)

REM 检查PyInstaller
pyinstaller --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: PyInstaller未安装
    echo 正在安装PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo ❌ PyInstaller安装失败
        pause
        exit /b 1
    )
)

echo ✓ PyInstaller 已安装
echo.

REM 显示菜单
echo 请选择打包模式:
echo 1. 发布版本 (推荐)
echo 2. 调试版本 (显示控制台)
echo 3. 退出
echo.

set /p choice="请输入选择 (1-3): "

if "%choice%"=="1" goto release
if "%choice%"=="2" goto debug
if "%choice%"=="3" goto exit
echo ❌ 无效选择，请重新运行脚本
pause
exit /b 1

:release
echo 🚀 开始发布版本打包...
goto build

:debug
echo 🔍 开始调试版本打包...
set debug_flag=--debug all
goto build

:build
echo ============================================================
echo 正在检测项目文件...

REM 自动检测Cython文件
set cython_file=
for %%f in (worker_threads_cy*.pyd) do set cython_file=%%f
if defined cython_file (
    echo ✓ 找到Cython文件: %cython_file%
) else (
    echo ⚠ 未找到Cython文件，将跳过相关依赖
)

REM 检测runtime hooks
set hooks=
if exist runtime_hook.py set hooks=%hooks% runtime_hook.py
if exist runtime_hook_multiprocessing.py set hooks=%hooks% runtime_hook_multiprocessing.py
if defined hooks (
    echo ✓ 找到runtime hooks: %hooks%
) else (
    echo ⚠ 未找到runtime hooks
)

echo ============================================================
echo 开始执行打包命令...

REM 构建基础命令
set cmd=pyinstaller --noconfirm --onefile --collect-all numpy --collect-all pandas --collect-all PyQt5 --collect-all billiard --collect-all psutil

REM 添加Cython文件
if defined cython_file (
    set cmd=%cmd% --collect-all worker_threads_cy
)

REM 添加隐藏导入
set cmd=%cmd% --hidden-import billiard --hidden-import billiard.pool --hidden-import billiard.managers --hidden-import billiard.connection --hidden-import billiard.synchronize --hidden-import billiard.heap --hidden-import billiard.queues --hidden-import billiard.process --hidden-import billiard.socket --hidden-import billiard.forking --hidden-import billiard.spawn --hidden-import billiard.util --hidden-import billiard.compat --hidden-import multiprocessing --hidden-import multiprocessing.pool --hidden-import multiprocessing.managers --hidden-import multiprocessing.synchronize --hidden-import multiprocessing.heap --hidden-import multiprocessing.queues --hidden-import multiprocessing.process --hidden-import multiprocessing.socket --hidden-import multiprocessing.forking --hidden-import multiprocessing.spawn --hidden-import multiprocessing.util --hidden-import multiprocessing.compat --hidden-import function --hidden-import ui --hidden-import worker_threads

REM 添加runtime hooks
if defined hooks (
    for %%h in (%hooks%) do set cmd=%cmd% --runtime-hook %%h
)

REM 添加数据文件
if defined cython_file (
    set cmd=%cmd% --add-data "%cython_file%;."
)
if exist runtime_hook.py set cmd=%cmd% --add-data "runtime_hook.py;."
if exist runtime_hook_multiprocessing.py set cmd=%cmd% --add-data "runtime_hook_multiprocessing.py;."
if exist function set cmd=%cmd% --add-data "function;function"
if exist ui set cmd=%cmd% --add-data "ui;ui"

REM 添加输出路径
set cmd=%cmd% --distpath ./dist --workpath ./build --specpath .

REM 添加调试标志
if defined debug_flag set cmd=%cmd% %debug_flag%

REM 添加主文件
set cmd=%cmd% main.py

echo 完整打包命令:
echo %cmd%
echo ============================================================

REM 执行打包
%cmd%

if errorlevel 1 (
    echo ❌ 打包失败！
    echo 请检查错误信息
) else (
    echo ✅ 打包成功完成！
    echo 输出文件位置: ./dist/main.exe
    
    REM 询问是否测试
    set /p test_choice="是否立即测试打包后的程序？(y/N): "
    if /i "%test_choice%"=="y" (
        if exist ".\dist\main.exe" (
            echo 🚀 启动测试程序...
            start "" ".\dist\main.exe"
        ) else (
            echo ❌ 未找到打包后的程序
        )
    )
)

:exit
echo.
echo 按任意键退出...
pause >nul
