# Testa a Pokédex no programa EMPACOTADO, como uma pessoa usaria: descompacta o ZIP numa pasta nova, abre sem
# Python no PATH (pasta de dados temporária: nenhuma conta real), aperta Ctrl+D, confere que a Pokédex abriu
# (o botão Pokédex do topo fica ligado e aparece "Todas as contas"), tira um print, fecha no X e confere que
# não sobrou processo.
#   powershell -File ferramentas\pokedex\teste_build.ps1 -Zip dist_novo\PokeNexus-pokedex-teste.zip -Print <arquivo.png>
param([Parameter(Mandatory)] [string]$Zip, [string]$Print = "")
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "..\atualizacao\teste_app.ps1")
Add-Type -AssemblyName System.Windows.Forms

$pasta = Join-Path ([IO.Path]::GetTempPath()) ("pn_build_" + [Guid]::NewGuid().ToString("N").Substring(0, 8))
Expand-Archive $Zip $pasta
$exe = Get-ChildItem $pasta -Recurse -Filter PokeNexus.exe | Select-Object -First 1
$dados = Join-Path $pasta "dados"
New-Item -ItemType Directory $dados | Out-Null

$psi = New-Object Diagnostics.ProcessStartInfo $exe.FullName
$psi.UseShellExecute = $false
$psi.EnvironmentVariables["POKENEXUS_DATA"] = $dados
$psi.EnvironmentVariables["PATH"] = "$env:SystemRoot\system32;$env:SystemRoot"      # sem Python nenhum
$psi.EnvironmentVariables.Remove("PYTHONPATH")
$psi.EnvironmentVariables.Remove("PYTHONHOME")
$proc = [Diagnostics.Process]::Start($psi)
try {
    $h = Janela-De $proc
    Start-Sleep 6
    "PATH do processo sem python: " + (-not ($psi.EnvironmentVariables["PATH"] -match "python"))
    [Janela]::SetForegroundWindow($h) | Out-Null
    Start-Sleep -Milliseconds 300
    [Windows.Forms.SendKeys]::SendWait("^d")                 # Ctrl+D: a Pokédex
    Start-Sleep 2
    $raiz = [Windows.Automation.AutomationElement]::FromHandle($h)
    $acha = { param($nome) $raiz.FindFirst([Windows.Automation.TreeScope]::Descendants,
        (New-Object Windows.Automation.PropertyCondition ([Windows.Automation.AutomationElement]::NameProperty), $nome)) }
    $bd = & $acha " Pokédex"
    $estado = if ($bd) { $bd.GetCurrentPattern([Windows.Automation.TogglePattern]::Pattern).Current.ToggleState } else { "não achou" }
    "botão Pokédex do topo: $estado"
    "a Pokédex está à vista (botão Todas as contas): " + [bool](& $acha "Todas as contas")
    "a busca da Pokédex: " + [bool](& $acha "Buscar na Pokédex")
    if ($Print) { Print-Janela $proc $Print }
} finally {
    $sobrou = Fechar-PokeNexus $proc
}
"fechou no X: saiu=" + $proc.HasExited + " código=" + $proc.ExitCode + " processos que sobraram=" + $sobrou.Count
"crash.log: " + (Test-Path (Join-Path $dados "logs\crash.log"))
Remove-Item -Recurse -Force $pasta -ErrorAction SilentlyContinue
