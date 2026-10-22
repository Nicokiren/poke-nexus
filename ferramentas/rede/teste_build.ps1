# Testa o DNS seguro e os erros em português no programa EMPACOTADO, como uma pessoa usaria: descompacta o ZIP
# numa pasta nova, abre sem Python no PATH (pasta de dados temporária: nenhuma conta real), clica "Começar tudo",
# lê o contador do topo e a frase na tela, tira um print (PrintWindow: só a janela), fecha no X e confere que não
# sobrou processo.
#   powershell -File ferramentas\rede\teste_build.ps1 -Zip dist_novo\PokeNexus-dns-teste.zip -Print <png> [-SemDns] [-NetLog <json>]
#   -SemDns  o pokeidle.io "não existe" SÓ para este processo (--host-resolver-rules); a rede do PC não é tocada.
param([Parameter(Mandatory)] [string]$Zip, [string]$Print = "", [switch]$SemDns, [string]$NetLog = "")
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "..\atualizacao\teste_app.ps1")

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
$flags = @()
if ($SemDns) { $flags += '--host-resolver-rules="MAP pokeidle.io ~NOTFOUND"' }
if ($NetLog) { $flags += "--log-net-log=$NetLog"; $flags += "--net-log-capture-mode=Default" }     # caminho sem espaços
if ($flags) { $psi.EnvironmentVariables["QTWEBENGINE_CHROMIUM_FLAGS"] = $flags -join " " }
$proc = [Diagnostics.Process]::Start($psi)
try {
    $h = Janela-De $proc
    Start-Sleep 5
    "PATH do processo sem python: " + (-not ($psi.EnvironmentVariables["PATH"] -match "python"))
    "clicou Começar tudo: " + (Clicar $proc "Começar tudo")
    Start-Sleep 30
    $proc.Refresh()
    $raiz = [Windows.Automation.AutomationElement]::FromHandle((Janela-De $proc))     # a janela pode ter trocado de handle
    $textos = $raiz.FindAll([Windows.Automation.TreeScope]::Descendants, [Windows.Automation.Condition]::TrueCondition) |
        ForEach-Object { $_.Current.Name } | Where-Object { $_ }
    "contador do topo: " + (($textos | Where-Object { $_ -match "^\d/\d jogando$" }) -join ", ")
    "frase do erro na tela: " + (($textos | Where-Object { $_ -match "^Não consegui" } | Select-Object -Unique) -join " | ")
    if ($Print) { Print-Janela $proc $Print }
} finally {
    $sobrou = Fechar-PokeNexus $proc
}
"fechou no X: saiu=" + $proc.HasExited + " código=" + $proc.ExitCode + " processos que sobraram=" + $sobrou.Count
"crash.log: " + (Test-Path (Join-Path $dados "logs\crash.log"))
$log = Get-ChildItem (Join-Path $dados "logs") -Filter *.log | ForEach-Object { Get-Content $_.FullName -Encoding UTF8 }
"linhas do log com o código original: " + @($log | Where-Object { $_ -match "ERR_NAME_NOT_RESOLVED" }).Count
"linhas do log com a frase traduzida: " + @($log | Where-Object { $_ -match "Não consegui" }).Count
Remove-Item -Recurse -Force $pasta -ErrorAction SilentlyContinue
