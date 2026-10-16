; Instalador do PokeNexus (Inno Setup 6). Gerado pelo GitHub Actions (.github/workflows/release.yml) ou
; pelo build.bat, depois do PyInstaller:
;
;   ISCC.exe /DVERSAO=1.1.57 instalador\PokeNexus.iss
;
; Instala POR USUÁRIO, sem pedir administrador, em %LOCALAPPDATA%\Programs\PokeNexus.
; Os dados (%LOCALAPPDATA%\PokeNexus: logins, config.toml, logs) NUNCA são tocados: nem aqui, nem na
; atualização, nem no desinstalador. Eles moram em outra pasta e o instalador não sabe deles.

#ifndef VERSAO
  #define VERSAO "1.1-dev"
#endif
#ifndef ORIGEM
  #define ORIGEM "..\dist\PokeNexus"
#endif
#ifndef SAIDA
  #define SAIDA "..\dist"
#endif

[Setup]
; O AppId identifica o PokeNexus no Windows (atualizar por cima, desinstalar). NUNCA troque.
AppId={{1A74747E-E397-49F0-BC24-25F535B41F92}
AppName=PokeNexus
AppVersion={#VERSAO}
AppVerName=PokeNexus {#VERSAO}
AppPublisher=PokeNexus
AppPublisherURL=https://github.com/PauloAfonsoGR/poke-nexus
AppSupportURL=https://github.com/PauloAfonsoGR/poke-nexus/releases
PrivilegesRequired=lowest
DefaultDirName={localappdata}\Programs\PokeNexus
; Instalar por cima de uma versão já instalada usa a mesma pasta, sem perguntar de novo.
UsePreviousAppDir=yes
DisableDirPage=auto
DisableProgramGroupPage=yes
DisableReadyPage=yes
OutputDir={#SAIDA}
OutputBaseFilename=PokeNexus-Setup-{#VERSAO}
SetupIconFile=..\assets\pokenexus.ico
UninstallDisplayIcon={app}\PokeNexus.exe
UninstallDisplayName=PokeNexus
WizardStyle=modern
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; O próprio PokeNexus se fecha antes de atualizar (as contas param com segurança). Se mesmo assim ele
; estiver aberto, o instalador pede para fechar; não reabre pelo Restart Manager (quem reabre é o [Run]).
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "pt"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[CustomMessages]
pt.AtalhoArea=Criar atalho na Área de Trabalho
pt.Abrir=Abrir o PokeNexus
pt.DadosFicam=O PokeNexus foi removido.%n%nOs logins das contas, a configuração e os logs NÃO foram apagados. Eles ficam em:%n%n%1%n%nSe quiser apagar tudo, apague essa pasta à mão.

[Tasks]
Name: "desktopicon"; Description: "{cm:AtalhoArea}"

[InstallDelete]
; Atualização: tira os arquivos da versão anterior antes de copiar os novos (uma DLL antiga esquecida
; na pasta pode quebrar o Qt). Só a pasta do programa; os dados ficam em outra pasta.
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "{#ORIGEM}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\PokeNexus"; Filename: "{app}\PokeNexus.exe"
Name: "{autodesktop}\PokeNexus"; Filename: "{app}\PokeNexus.exe"; Tasks: desktopicon

[Run]
; Instalação normal: a última tela tem "Abrir o PokeNexus" marcado.
Filename: "{app}\PokeNexus.exe"; Description: "{cm:Abrir}"; Flags: nowait postinstall skipifsilent
; Atualização pelo botão "Atualizar" (modo silencioso): o PokeNexus reabre sozinho.
Filename: "{app}\PokeNexus.exe"; Flags: nowait; Check: WizardSilent

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
    SuppressibleMsgBox(FmtMessage(CustomMessage('DadosFicam'), [ExpandConstant('{localappdata}\PokeNexus')]),
                       mbInformation, MB_OK, IDOK);
end;
