@echo off
rem Junta os registros (logs) e a configuracao do PokeNexus num ZIP na Area de Trabalho, para mandar
rem para quem esta testando. NAO leva a pasta "profiles" (logins, cookies e senhas ficam fora).
setlocal
set "DADOS=%LOCALAPPDATA%\PokeNexus"
if not exist "%DADOS%" (
  echo Nao achei a pasta de dados do PokeNexus em "%DADOS%".
  echo Abra o PokeNexus pelo menos uma vez antes.
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$d = $env:LOCALAPPDATA + '\PokeNexus';" ^
  "$tmp = Join-Path $env:TEMP ('pokenexus_relatorio_' + [guid]::NewGuid());" ^
  "New-Item -ItemType Directory $tmp | Out-Null;" ^
  "if (Test-Path ($d + '\logs')) { Copy-Item ($d + '\logs') $tmp -Recurse };" ^
  "if (Test-Path ($d + '\config.toml')) { Copy-Item ($d + '\config.toml') $tmp };" ^
  "Get-ComputerInfo -Property OsName,OsVersion,CsProcessors,CsTotalPhysicalMemory -ErrorAction SilentlyContinue | Out-File (Join-Path $tmp 'pc.txt');" ^
  "Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion | Out-File (Join-Path $tmp 'pc.txt') -Append;" ^
  "$destino = Join-Path ([Environment]::GetFolderPath('Desktop')) 'PokeNexus-relatorio.zip';" ^
  "Compress-Archive -Path (Join-Path $tmp '*') -DestinationPath $destino -Force;" ^
  "Remove-Item $tmp -Recurse -Force;" ^
  "Write-Host ('Pronto: ' + $destino)"
echo.
echo Mande o arquivo PokeNexus-relatorio.zip (na Area de Trabalho) para quem pediu.
pause
