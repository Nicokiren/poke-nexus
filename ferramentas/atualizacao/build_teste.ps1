# Build de TESTE com um número de versão (como o GitHub Actions faz), numa pasta à parte:
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File ferramentas\atualizacao\build_teste.ps1 -Versao 1.1.1
#
# Resultado em dist_teste\<versão>\: PokeNexus\ (a pasta do programa) e PokeNexus-Setup-<versão>.exe.
# Nada é publicado. O app\_build.py é apagado no fim (rodando do código a versão volta a ser "1.1-dev").
param([Parameter(Mandatory = $true)][string]$Versao)
$ErrorActionPreference = "Stop"
$raiz = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $raiz
$saida = Join-Path $raiz "dist_teste\$Versao"
New-Item -ItemType Directory -Force $saida | Out-Null
$build = Join-Path $raiz "app\_build.py"
try {
    [IO.File]::WriteAllText($build, "VERSAO = `"$Versao`"`nCOMMIT = `"teste`"`n")
    & .venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --distpath $saida --workpath (Join-Path $raiz "build_teste\$Versao") PokeNexus.spec
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller falhou" }
} finally {
    Remove-Item $build -ErrorAction SilentlyContinue
}
$iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe", "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
          "$env:ProgramFiles\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) { throw "Inno Setup 6 não encontrado" }
& $iscc /Q "/DVERSAO=$Versao" "/DORIGEM=$saida\PokeNexus" "/DSAIDA=$saida" instalador\PokeNexus.iss
if ($LASTEXITCODE -ne 0) { throw "Inno Setup falhou" }
Get-ChildItem $saida -File | Select-Object Name, @{n = "MB"; e = { [math]::Round($_.Length / 1MB, 1) } }
