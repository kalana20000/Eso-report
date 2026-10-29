@echo off
echo ===================================================
echo  Starting GeoRank SEO Local Rank Tracker...
echo ===================================================
echo.

if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)

python app.py
pause
