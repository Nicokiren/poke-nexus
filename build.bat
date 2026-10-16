@echo off
REM ==============================================================
REM  Gera a versao final do PokeNexus (SO PARA O DESENVOLVEDOR).
REM  Resultado:  dist\PokeNexus\PokeNexus.exe   e   dist\PokeNexus-<versao>.zip
REM  O usuario final so recebe o ZIP: descompacta e da dois cliques no .exe.
REM ==============================================================
chcp 65001 >nul
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  echo Python nao encontrado. Instale o Python 3.11+ de https://www.python.org/downloads/
  pause & exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  echo Criando ambiente Python...
  py -m venv .venv || goto erro
)
echo Instalando dependencias de build...
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul || goto erro
".venv\Scripts\python.exe" -m pip install -r requirements.txt pyinstaller || goto erro

echo Gerando o executavel...
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean PokeNexus.spec || goto erro

set VERSAO=
for /f "usebackq delims=" %%v in (`.venv\Scripts\python.exe -c "from app.config import APP_VERSION; print(APP_VERSION)"`) do set VERSAO=%%v
if "%VERSAO%"=="" set VERSAO=dev
echo Compactando dist\PokeNexus-%VERSAO%.zip ...
powershell -NoProfile -Command "Compress-Archive -Path 'dist\PokeNexus' -DestinationPath 'dist\PokeNexus-%VERSAO%.zip' -Force" || goto erro

echo.
echo Pronto!
echo   dist\PokeNexus\PokeNexus.exe     ZIP: dist\PokeNexus-%VERSAO%.zip
echo   (o ZIP e o que se entrega ao usuario; o Modo Leve liga e desliga nas Configuracoes)
pause
exit /b 0

:erro
echo.
echo O build falhou. Veja a mensagem acima.
pause
exit /b 1
