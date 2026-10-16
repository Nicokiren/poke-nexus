# Trava 2 do build (teste de fumaça): o PokeNexus empacotado abre, fica de pé e fecha sem sobrar processo.
# Usado pelo GitHub Actions antes de publicar e dá para rodar à mão:
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File instalador\fumaca.ps1 [-Exe dist\PokeNexus\PokeNexus.exe]
#
# Pasta de dados temporária (POKENEXUS_DATA): nenhuma conta e nenhum dado do usuário é tocado.
param(
    [string]$Exe = "dist\PokeNexus\PokeNexus.exe",
    [int]$Segundos = 25
)
$ErrorActionPreference = "Stop"
$exe = (Resolve-Path $Exe).Path
$pasta = Split-Path $exe
$dados = Join-Path ([IO.Path]::GetFullPath($env:TEMP)) ("pn_fumaca_" + [guid]::NewGuid().ToString("N").Substring(0, 8))
New-Item -ItemType Directory $dados | Out-Null

function Do-Pacote { @(Get-Process | Where-Object { $_.Path -and $_.Path.StartsWith($pasta, [StringComparison]::OrdinalIgnoreCase) }) }

$psi = New-Object Diagnostics.ProcessStartInfo $exe
$psi.UseShellExecute = $false
$psi.EnvironmentVariables["POKENEXUS_DATA"] = $dados
$p = [Diagnostics.Process]::Start($psi)
Write-Host "PokeNexus aberto (PID $($p.Id)); esperando $Segundos s..."
Start-Sleep -Seconds $Segundos
$falhas = @()
if ($p.HasExited) { $falhas += "o processo fechou sozinho (código $($p.ExitCode))" }
$crash = Join-Path $dados "logs\crash.log"
if (Test-Path $crash) { $falhas += "apareceu logs\crash.log:`n" + (Get-Content $crash -Raw) }

if (-not $p.HasExited) {
    # Fecha como o X da janela (WM_CLOSE). Sem janela à vista (sessão sem área de trabalho), encerra.
    $p.Refresh()
    $fechou = $p.CloseMainWindow()
    if (-not $p.WaitForExit(30000)) {
        if ($fechou) { $falhas += "não fechou em 30 s depois do X" }
        Write-Host "sem janela para fechar no X: encerrando a árvore do processo"
        taskkill /PID $p.Id /T /F | Out-Null
        $p.WaitForExit(15000) | Out-Null
    }
}
Start-Sleep -Seconds 3
$sobra = Do-Pacote
if ($sobra.Count) { $falhas += "sobrou processo: " + (($sobra | ForEach-Object { "$($_.Name) ($($_.Id))" }) -join ", "); $sobra | Stop-Process -Force }
Remove-Item -Recurse -Force $dados -ErrorAction SilentlyContinue

if ($falhas.Count) {
    Write-Host "FUMAÇA FALHOU:"; $falhas | ForEach-Object { Write-Host " - $_" }
    exit 1
}
Write-Host "Fumaça ok: abriu, ficou $Segundos s de pé, sem crash.log, fechou e não sobrou processo."
exit 0
