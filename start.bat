@echo off
title CampusAI Development Server ^& Auto-Login
echo ========================================================================
echo   CAMPUS AI - STARTING LOCAL DEVELOPMENT WITH AUTO-LOGIN
echo ========================================================================
echo.
echo Automatically starting services and launching browser:
echo   [User Portal]:  http://localhost:3000/login?autologin=true
echo   [Admin Portal]: http://localhost:3001/login?autologin=superadmin
echo.
echo Keep this command prompt window open while testing the application.
echo ========================================================================
echo.
node scripts/start-dev.js --open
pause
