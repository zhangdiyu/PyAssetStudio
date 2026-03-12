@echo off
:: Run as administrator to register file associations
:: This will associate .unity3d, .ab, .bundle, .assets files with PyAssetStudio

echo Registering file associations for PyAssetStudio...
echo Please run this script as Administrator!
echo.

python asset_studio.py --register

echo.
pause
