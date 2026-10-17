# Testa a calculadora no programa EMPACOTADO, como uma pessoa usaria: descompacta o ZIP numa pasta nova,
# abre sem Python no PATH (pasta de dados temporária: nenhuma conta real), vai ao Mercado, abre a
# calculadora, digita 1000 em Gemas pelo teclado, lê o campo de dólares, tira um print, fecha no X e
# confere que não sobrou processo.
#   powershell -File ferramentas\calculadora\teste_build.ps1 -Zip dist_novo\PokeNexus-teste.zip -Print <arquivo.png>
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

# Ctrl+M (o atalho do Mercado): em janela estreita os botões da barra ficam só com o ícone, sem nome
[Janela]::SetForegroundWindow($h) | Out-Null
Start-Sleep -Milliseconds 300
[Windows.Forms.SendKeys]::SendWait("^m")
Start-Sleep 1
$raiz = [Windows.Automation.AutomationElement]::FromHandle($h)
# o botão Calculadora liga e desliga: para a automação ele é uma "caixa de seleção" (Toggle)
$nome = New-Object Windows.Automation.PropertyCondition ([Windows.Automation.AutomationElement]::NameProperty), " Calculadora"
$bc = $raiz.FindFirst([Windows.Automation.TreeScope]::Descendants, $nome)
$bc.GetCurrentPattern([Windows.Automation.TogglePattern]::Pattern).Toggle()
Start-Sleep 1
"Calculadora aberta: " + ($bc.GetCurrentPattern([Windows.Automation.TogglePattern]::Pattern).Current.ToggleState)

$cond = New-Object Windows.Automation.PropertyCondition ([Windows.Automation.AutomationElement]::ControlTypeProperty),
                                                         ([Windows.Automation.ControlType]::Edit)
$campos = @{}
foreach ($e in $raiz.FindAll([Windows.Automation.TreeScope]::Descendants, $cond)) {
    $n = $e.Current.Name
    if ($n -eq "Gemas") { $campos["gemas"] = $e }
    if ($n -like "D*lares (US$)") { $campos["dolares"] = $e }
}
"campos achados: " + ($campos.Keys -join ", ")
[Janela]::SetForegroundWindow($h) | Out-Null
$campos["gemas"].SetFocus()
Start-Sleep -Milliseconds 300
[Windows.Forms.SendKeys]::SendWait("1000")
Start-Sleep -Milliseconds 500
$valor = $campos["dolares"].GetCurrentPattern([Windows.Automation.ValuePattern]::Pattern).Current.Value
"digitou 1000 em Gemas, Dólares mostra: '$valor' " + $(if ($valor -eq "9,00") { "(ok)" } else { "(FALHA)" })
if ($Print) { Print-Janela $proc $Print }
} finally {
$sobrou = Fechar-PokeNexus $proc
}
"fechou no X: saiu=" + $proc.HasExited + " código=" + $proc.ExitCode + " processos que sobraram=" + $sobrou.Count
"crash.log: " + (Test-Path (Join-Path $dados "logs\crash.log"))
Remove-Item -Recurse -Force $pasta -ErrorAction SilentlyContinue
