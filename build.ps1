# PowerShell 智能打包脚本
# 使用方法: 右键 -> "使用PowerShell运行" 或 在PowerShell中执行 .\build.ps1

param(
    [string]$Mode = "release"
)

# 设置控制台编码
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "🔧 PyInstaller 智能打包脚本" -ForegroundColor Cyan
Write-Host "===========================================================" -ForegroundColor Cyan

# 检查Python环境
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Python环境: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ 错误: 未找到Python环境" -ForegroundColor Red
    Write-Host "请确保Python已正确安装并添加到PATH" -ForegroundColor Yellow
    Read-Host "按回车键退出"
    exit 1
}

# 检查PyInstaller
try {
    $pyinstallerVersion = pyinstaller --version 2>&1
    Write-Host "✓ PyInstaller: $pyinstallerVersion" -ForegroundColor Green
} catch {
    Write-Host "⚠ PyInstaller未安装，正在安装..." -ForegroundColor Yellow
    try {
        pip install pyinstaller
        Write-Host "✓ PyInstaller安装成功" -ForegroundColor Green
    } catch {
        Write-Host "❌ PyInstaller安装失败" -ForegroundColor Red
        Read-Host "按回车键退出"
        exit 1
    }
}

Write-Host ""

# 显示菜单（如果不是通过参数指定模式）
if ($Mode -eq "release" -and $args.Count -eq 0) {
    Write-Host "请选择打包模式:" -ForegroundColor White
    Write-Host "1. 发布版本 (推荐)" -ForegroundColor Green
    Write-Host "2. 调试版本 (显示控制台)" -ForegroundColor Yellow
    Write-Host "3. 退出" -ForegroundColor Red
    Write-Host ""
    
    do {
        $choice = Read-Host "请输入选择 (1-3)"
        switch ($choice) {
            "1" { $Mode = "release"; break }
            "2" { $Mode = "debug"; break }
            "3" { exit 0 }
            default { Write-Host "❌ 无效选择，请输入 1、2 或 3" -ForegroundColor Red }
        }
    } while ($choice -notin @("1", "2", "3"))
}

# 显示选择的模式
switch ($Mode) {
    "release" { 
        Write-Host "🚀 开始发布版本打包..." -ForegroundColor Green
        $debugFlag = ""
    }
    "debug" { 
        Write-Host "🔍 开始调试版本打包..." -ForegroundColor Yellow
        $debugFlag = "--debug all"
    }
}

Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host "正在检测项目文件..." -ForegroundColor White

# 自动检测Cython文件
$cythonFile = Get-ChildItem -Name "worker_threads_cy*.pyd" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($cythonFile) {
    Write-Host "✓ 找到Cython文件: $cythonFile" -ForegroundColor Green
} else {
    Write-Host "⚠ 未找到Cython文件，将跳过相关依赖" -ForegroundColor Yellow
}

# 检测runtime hooks
$hooks = @()
if (Test-Path "runtime_hook.py") { $hooks += "runtime_hook.py" }
if (Test-Path "runtime_hook_multiprocessing.py") { $hooks += "runtime_hook_multiprocessing.py" }
if ($hooks.Count -gt 0) {
    Write-Host "✓ 找到runtime hooks: $($hooks -join ', ')" -ForegroundColor Green
} else {
    Write-Host "⚠ 未找到runtime hooks" -ForegroundColor Yellow
}

Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host "开始执行打包命令..." -ForegroundColor White

# 构建基础命令
$cmd = @(
    "pyinstaller",
    "--noconfirm",
    "--onefile",
    "--collect-all", "numpy",
    "--collect-all", "pandas",
    "--collect-all", "PyQt5",
    "--collect-all", "billiard",
    "--collect-all", "psutil"
)

# 添加Cython文件
if ($cythonFile) {
    $cmd += "--collect-all", "worker_threads_cy"
}

# 添加隐藏导入
$hiddenImports = @(
    "billiard", "billiard.pool", "billiard.connection", "billiard.managers",
    "billiard.synchronize", "billiard.heap", "billiard.queues", "billiard.process",
    "billiard.socket", "billiard.forking", "billiard.spawn", "billiard.util", "billiard.compat",
    "multiprocessing", "multiprocessing.pool", "multiprocessing.managers", "multiprocessing.synchronize",
    "multiprocessing.heap", "multiprocessing.queues", "multiprocessing.process", "multiprocessing.socket",
    "multiprocessing.forking", "multiprocessing.spawn", "multiprocessing.util", "multiprocessing.compat",
    "function", "ui", "worker_threads"
)

foreach ($imp in $hiddenImports) {
    $cmd += "--hidden-import", $imp
}

# 添加runtime hooks
foreach ($hook in $hooks) {
    $cmd += "--runtime-hook", $hook
}

# 添加数据文件
if ($cythonFile) {
    $cmd += "--add-data", "$cythonFile;."
}
if (Test-Path "runtime_hook.py") {
    $cmd += "--add-data", "runtime_hook.py;."
}
if (Test-Path "runtime_hook_multiprocessing.py") {
    $cmd += "--add-data", "runtime_hook_multiprocessing.py;."
}
if (Test-Path "function") {
    $cmd += "--add-data", "function;function"
}
if (Test-Path "ui") {
    $cmd += "--add-data", "ui;ui"
}

# 添加输出路径
$cmd += "--distpath", "./dist", "--workpath", "./build", "--specpath", "."

# 添加调试标志
if ($debugFlag) {
    $cmd += $debugFlag.Split(" ")
}

# 添加主文件
$cmd += "main.py"

# 显示完整命令
Write-Host "完整打包命令:" -ForegroundColor Cyan
Write-Host ($cmd -join " ") -ForegroundColor White
Write-Host "===========================================================" -ForegroundColor Cyan

# 执行打包
try {
    Write-Host "正在执行打包，请稍候..." -ForegroundColor Yellow
    $result = & $cmd[0] $cmd[1..($cmd.Length-1)] 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ 打包成功完成！" -ForegroundColor Green
        Write-Host "输出文件位置: ./dist/main.exe" -ForegroundColor Green
        
        # 询问是否测试
        $testChoice = Read-Host "是否立即测试打包后的程序？(y/N)"
        if ($testChoice -eq "y" -or $testChoice -eq "Y") {
            $exePath = ".\dist\main.exe"
            if (Test-Path $exePath) {
                Write-Host "🚀 启动测试程序..." -ForegroundColor Green
                Start-Process $exePath
            } else {
                Write-Host "❌ 未找到打包后的程序" -ForegroundColor Red
            }
        }
    } else {
        Write-Host "❌ 打包失败！" -ForegroundColor Red
        Write-Host "错误输出:" -ForegroundColor Red
        Write-Host $result -ForegroundColor Red
    }
} catch {
    Write-Host "❌ 打包执行出错: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "按回车键退出..." -ForegroundColor White
Read-Host
