echo off
set msg=%1
echo %msg%
git add .
git commit -m "%msg%"
git push origin main