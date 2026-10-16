# Monta o ZIP para mandar a amigos testarem: a pasta do programa + LEIA-ME + o atalho que junta os logs.
#   powershell -ExecutionPolicy Bypass -File ferramentas\pacote_amigos\montar.ps1 [-Origem dist_novo\PokeNexus]
# A origem é uma pasta gerada pelo PyInstaller (padrão: dist\PokeNexus). Nada da pasta de dados do
# usuário (logins, logs) entra: o script recusa se achar algo parecido.
param([string]$Origem = "dist\PokeNexus")
$ErrorActionPreference = "Stop"
$raiz = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $raiz
$Origem = (Resolve-Path $Origem).Path
if (-not (Test-Path (Join-Path $Origem "PokeNexus.exe"))) { throw "Não achei PokeNexus.exe em $Origem" }
$suspeitos = Get-ChildItem $Origem -Recurse -Directory | Where-Object { $_.Name -in @("profiles", "logs", "web") }
if ($suspeitos) { throw "A origem tem pastas de dados de usuário: $($suspeitos.FullName -join ', ')" }
$versao = (& ".venv\Scripts\python.exe" -c "from app.config import APP_VERSION; print(APP_VERSION)").Trim()
$nome = "PokeNexus-$versao"
$tmp = Join-Path $env:TEMP "pokenexus_pacote_$([guid]::NewGuid())"
$pasta = Join-Path $tmp $nome
New-Item -ItemType Directory $pasta | Out-Null
Copy-Item $Origem (Join-Path $pasta "PokeNexus") -Recurse
$leia = (Get-Content (Join-Path $PSScriptRoot "LEIA-ME.txt") -Raw -Encoding UTF8).Replace("{VERSAO}", $versao).Replace("{DATA}", (Get-Date -Format "dd/MM/yyyy"))
[IO.File]::WriteAllText((Join-Path $pasta "LEIA-ME.txt"), $leia.Replace("`r`n", "`n").Replace("`n", "`r`n"), (New-Object Text.UTF8Encoding $true))
Copy-Item (Join-Path $PSScriptRoot "Juntar relatorio para enviar.bat") $pasta
New-Item -ItemType Directory -Force "dist" | Out-Null
$zip = Join-Path $raiz "dist\$nome-para-amigos.zip"
if (Test-Path $zip) { Remove-Item $zip }
Compress-Archive -Path $pasta -DestinationPath $zip -CompressionLevel Optimal
Remove-Item $tmp -Recurse -Force
"{0}  ({1:N0} MB)" -f $zip, ((Get-Item $zip).Length / 1MB)
