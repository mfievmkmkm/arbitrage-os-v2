@echo off
setlocal
cd /d "%~dp0\.."
where git >nul 2>nul
if errorlevel 1 (
  echo Install Git for Windows first, then run this script again.
  exit /b 1
)
if not exist .git (
  echo This source folder has no Git metadata. Clone the delivered bundle first.
  echo git clone ..\arbitrage-os-v2.bundle ..\arbitrage-os-v2-git
  echo Then run this script inside the cloned repository.
  exit /b 1
)
git merge-base --is-ancestor dc7a92e HEAD
if errorlevel 1 exit /b 1
git merge-base --is-ancestor f8db3be HEAD
if errorlevel 1 exit /b 1
git remote get-url origin >nul 2>nul
if errorlevel 1 (
  git remote add origin https://github.com/mfievmkmkm/arbitrage-os-v2.git
) else (
  git remote set-url origin https://github.com/mfievmkmkm/arbitrage-os-v2.git
)
git push -u origin main
if errorlevel 1 (
  echo Push failed. Sign in using Git Credential Manager. Do not use force push.
  exit /b 1
)
git ls-remote origin refs/heads/main
endlocal
