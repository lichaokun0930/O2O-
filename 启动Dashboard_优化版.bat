@echo off
chcp 65001 >nul 2>&1
cls
echo ========================================
echo   O2O Dashboard v2.1 (Optimized)
echo ========================================
echo.
echo Optimizations:
echo   [OK] AI modules removed
echo   [OK] Data cache (5-10x faster)
echo   [OK] Logging system
echo   [OK] Column mapping fixed
echo.
echo Starting Dashboard...
echo.

python dashboard_v2_optimized.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ========================================
    echo Error occurred! Check logs/dashboard.log
    echo ========================================
)

pause
