; Inno Setup Installer Script for PennyBook
; Custom styled borderless 800x500 game-launcher style installer with Win32 polling dragging and custom close controls

#define MyAppName "PennyBook"
#define MyAppVersion "1.1.0"
#define MyAppPublisher "Sudeep Mullaguri"
#define MyAppURL "https://github.com/SUDEEPMULLAGURI/PennyBook"
#define MyAppExeName "PennyBook.exe"

[Setup]
AppId={{509E9623-CD2A-4FDF-A460-DF29B963557A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={code:GetDefaultDirName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputBaseFilename=PennyBookSetup
SetupIconFile=static\logo.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern

; Default placeholder graphics (Inno Setup requires these directives, we will animate them dynamically)
WizardImageFile=wizard_welcome.bmp
WizardSmallImageFile=wizard_small.bmp

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\PennyBook\*"; DestDir: "{app}"; Excludes: "pennybook.db,receipts\*"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "dist\PennyBook\pennybook.db"; DestDir: "{app}"; Flags: onlyifdoesntexist uninsneveruninstall; Permissions: users-modify
; Package the static welcome background to be extracted at runtime
Source: "wizard_welcome.bmp"; Flags: dontcopy
; Package the app logo separately (shown on Welcome page only)
Source: "app_logo.bmp"; Flags: dontcopy

[Dirs]
Name: "{app}"; Permissions: users-modify
Name: "{app}\receipts"; Permissions: users-modify

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
// Import Win32 API Timer functions from user32.dll
function SetTimer(hWnd: LongWord; nIDEvent: LongWord; uElapse: LongWord; lpTimerFunc: LongWord): LongWord;
  external 'SetTimer@user32.dll stdcall';

function KillTimer(hWnd: LongWord; uIDEvent: LongWord): Integer;
  external 'KillTimer@user32.dll stdcall';

// Import Win32 API functions from user32.dll for drag-to-move custom window handling
procedure ReleaseCapture();
  external 'ReleaseCapture@user32.dll stdcall';

function SendMessage(hWnd: HWND; Msg: LongWord; wParam: LongWord; lParam: LongWord): LongWord;
  external 'SendMessageW@user32.dll stdcall';

function GetAsyncKeyState(vKey: Integer): ShortInt;
  external 'GetAsyncKeyState@user32.dll stdcall';

function GetCursorPos(var lpPoint: TPoint): Boolean;
  external 'GetCursorPos@user32.dll stdcall';

function GetWindowRect(hWnd: HWND; var lpRect: TRect): Boolean;
  external 'GetWindowRect@user32.dll stdcall';

var
  TimerID: LongWord;
  FrameIndex: Integer;
  AnimTickCount: Integer;
  BgColor: TColor;
  HeaderBgColor: TColor;
  TxtColor: TColor;
  GoldColor: TColor;
  SubTextColor: TColor;
  
  // Custom Controls to prevent Inno Setup layout engine from overriding bounds
  CustomWelcomeBg: TBitmapImage;
  CustomWelcomeTitle: TLabel;
  CustomWelcomeDesc: TLabel;
  
  CustomFinishedBg: TBitmapImage;
  CustomFinishedTitle: TLabel;
  CustomFinishedDesc: TLabel;
  
  // Custom Close button
  CloseLabel: TLabel;

  // Custom Installation Mode choice page
  InstallModePage: TInputOptionWizardPage;

// Custom Close Button Click
procedure CloseLabelClick(Sender: TObject);
begin
  WizardForm.Close;
end;

// Win32 Timer callback procedure for handling dragging
procedure TimerCallback(hWnd: LongWord; uMsg: LongWord; idEvent: LongWord; dwTime: LongWord);
var
  MousePt: TPoint;
  FormRect: TRect;
begin
  try
    // ----------------- DRAGGING HOOK BY MOUSE POLLING -----------------
    // VK_LBUTTON = 1. If Left mouse button is down, check drag conditions
    if GetAsyncKeyState(1) < 0 then
    begin
      if GetCursorPos(MousePt) then
      begin
        if GetWindowRect(WizardForm.Handle, FormRect) then
        begin
          // Verify if cursor is inside the borderless launcher boundaries
          if (MousePt.X >= FormRect.Left) and (MousePt.X <= FormRect.Right) and
             (MousePt.Y >= FormRect.Top) and (MousePt.Y <= FormRect.Bottom) then
          begin
            // Drag is allowed only in the main body (above bottom button panel at height-60)
            // and not clicking directly on the custom 'X' close button at the top right
            if (MousePt.Y - FormRect.Top < WizardForm.ClientHeight - ScaleY(60)) and
               ((MousePt.X - FormRect.Left < WizardForm.ClientWidth - ScaleX(50)) or (MousePt.Y - FormRect.Top > ScaleY(50))) then
            begin
              // Dragging is allowed on Welcome Page, Finished Page, or the bottom bars of other pages
              if WizardForm.WelcomePage.Visible or WizardForm.FinishedPage.Visible then
              begin
                ReleaseCapture();
                SendMessage(WizardForm.Handle, $0112, $F012, 0); // WM_SYSCOMMAND, SC_MOVE + HTCAPTION
              end;
            end;
          end;
        end;
      end;
    end;
  except
    // Gracefully catch exceptions to prevent crash loops inside the callback
  end;
end;

// Helper to recursively color controls on setup pages
procedure ColorControls(Parent: TWinControl);
var
  I: Integer;
  Ctrl: TControl;
begin
  for I := 0 to Parent.ControlCount - 1 do
  begin
    Ctrl := Parent.Controls[I];
    
    // Style labels
    if Ctrl is TLabel then
    begin
      TLabel(Ctrl).Font.Color := TxtColor;
    end
    
    // Style Inno Setup static text controls (fixes invisible descriptions!)
    else if Ctrl is TNewStaticText then
    begin
      TNewStaticText(Ctrl).Font.Color := TxtColor;
    end
    
    // Style check boxes
    else if Ctrl is TCheckBox then
    begin
      TCheckBox(Ctrl).Font.Color := TxtColor;
      TCheckBox(Ctrl).Color := BgColor;
    end
    
    // Style radio buttons
    else if Ctrl is TRadioButton then
    begin
      TRadioButton(Ctrl).Font.Color := TxtColor;
      TRadioButton(Ctrl).Color := BgColor;
    end
    
    // Style panel containers
    else if Ctrl is TPanel then
    begin
      TPanel(Ctrl).Color := BgColor;
      ColorControls(TPanel(Ctrl));
    end
    
    // Style text inputs
    else if Ctrl is TEdit then
    begin
      TEdit(Ctrl).Color := HeaderBgColor;
      TEdit(Ctrl).Font.Color := TxtColor;
    end
    
    // Style list boxes
    else if Ctrl is TListBox then
    begin
      TListBox(Ctrl).Color := HeaderBgColor;
      TListBox(Ctrl).Font.Color := TxtColor;
    end
    
    // Style Inno Setup checklist boxes (transparent, borderless style)
    else if Ctrl is TNewCheckListBox then
    begin
      TNewCheckListBox(Ctrl).Color := BgColor;
      TNewCheckListBox(Ctrl).Font.Color := TxtColor;
      TNewCheckListBox(Ctrl).BorderStyle := bsNone;
    end
    
    // Style memo fields
    else if Ctrl is TMemo then
    begin
      TMemo(Ctrl).Color := HeaderBgColor;
      TMemo(Ctrl).Font.Color := TxtColor;
    end
    
    // Recurse window controls (containers)
    else if Ctrl is TWinControl then
    begin
      ColorControls(TWinControl(Ctrl));
    end;
  end;
end;

// Helper to draw the custom background grid and trendline on intermediate wizard pages
procedure CreatePageBackground(AParent: TWinControl);
var
  Bg: TBitmapImage;
begin
  Bg := TBitmapImage.Create(WizardForm);
  Bg.Parent := AParent;
  Bg.Left := 0;
  Bg.Top := 0;
  Bg.Width := AParent.Width;
  Bg.Height := AParent.Height;
  Bg.Stretch := True;
  if FileExists(ExpandConstant('{tmp}\wizard_welcome.bmp')) then
  begin
    Bg.Bitmap.LoadFromFile(ExpandConstant('{tmp}\wizard_welcome.bmp'));
  end;
  Bg.Enabled := False; // Click-transparent so inputs behind or drag handlers work
  Bg.SendToBack;
end;

// Helper to dynamically calculate folder path based on chosen installation mode
function GetDefaultDirName(Param: String): String;
begin
  if (InstallModePage <> nil) and (InstallModePage.SelectedValueIndex = 0) then
    Result := ExpandConstant('{commonpf}\{#MyAppName}')
  else
    Result := ExpandConstant('{localappdata}\Programs\{#MyAppName}');
end;

// Verify administrative privileges if "All Users" is selected
function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if (InstallModePage <> nil) and (CurPageID = InstallModePage.ID) then
  begin
    if InstallModePage.SelectedValueIndex = 0 then
    begin
      if not IsAdmin then
      begin
        MsgBox('Installing for All Users requires administrative privileges. Please restart the setup as Administrator, or choose "Only for me".', mbError, MB_OK);
        Result := False;
      end;
    end;
  end;
end;

procedure InitializeWizard();
var
  I: Integer;
  FileName: String;
  AppLogoImg: TBitmapImage;
begin
  // Extract background and logo
  ExtractTemporaryFile('wizard_welcome.bmp');
  ExtractTemporaryFile('app_logo.bmp');

  // ----------------- COLOR PALETTE CONFIG (DARK MODE) -----------------
  BgColor := $140F0E;       // #0e0f14 (Sidebar Dark)
  HeaderBgColor := BgColor;  // Merges the top panel seamlessly!
  TxtColor := $F7F5F5;       // #f5f5f7 (Off-White Text)
  GoldColor := $37AFD4;      // #d4af37 (Gold Accent)
  SubTextColor := $AAA1A1;   // #a1a1aa (Secondary Text)

  // ----------------- WINDOW STYLE OVERRIDES (BORDERLESS & RESIZED) -----------------
  WizardForm.BorderStyle := bsNone; // Borderless Game Launcher Style!
  WizardForm.Width := ScaleX(800);
  WizardForm.Height := ScaleY(500);

  // Style the primary forms
  WizardForm.Color := BgColor;
  WizardForm.InnerPage.Color := BgColor;
  WizardForm.WelcomePage.Color := BgColor;
  WizardForm.FinishedPage.Color := BgColor;
  WizardForm.MainPanel.Color := HeaderBgColor;

  // Set page notebooks to expand to the larger launcher resolution
  WizardForm.WelcomePage.Width := WizardForm.ClientWidth;
  WizardForm.WelcomePage.Height := WizardForm.ClientHeight;
  WizardForm.FinishedPage.Width := WizardForm.ClientWidth;
  WizardForm.FinishedPage.Height := WizardForm.ClientHeight;
  WizardForm.InnerPage.Width := WizardForm.ClientWidth;
  WizardForm.InnerPage.Height := ScaleY(372); // Stops at 430px (58 + 372) to prevent clipping buttons!

  // Disable the Welcome/Finished page panels so clicks fall through to the form's drag listener
  WizardForm.WelcomePage.Enabled := False;
  WizardForm.FinishedPage.Enabled := False;

  // Hide the horizontal bevel divider lines to merge top, middle, and bottom panels
  WizardForm.Bevel.Hide;
  WizardForm.Bevel1.Hide;

  // Apply the custom background grid and trendline to all intermediate pages
  CreatePageBackground(WizardForm.SelectDirPage);
  CreatePageBackground(WizardForm.SelectTasksPage);
  CreatePageBackground(WizardForm.ReadyPage);
  CreatePageBackground(WizardForm.InstallingPage);

  // ----------------- CREATE CUSTOM PRIVILEGES SELECTION PAGE -----------------
  InstallModePage := CreateInputOptionPage(
    wpWelcome,
    'Select Installation Mode',
    'Who should PennyBook be installed for?',
    'Please select whether you wish to make this software available for all users or just yourself.',
    True, // Radio buttons option
    False
  );
  InstallModePage.Add('Anyone who uses this computer (All Users - requires admin rights)');
  InstallModePage.Add('Only for me (Current User)');
  InstallModePage.SelectedValueIndex := 1; // Default to Current User (lowest privilege)
  
  // Overlay the premium background grid and trendline
  CreatePageBackground(InstallModePage.Surface);

  // ----------------- CREATE CUSTOM WELCOME PAGE -----------------
  // Hide standard Welcome page controls completely
  WizardForm.WelcomeLabel1.Hide;
  WizardForm.WelcomeLabel2.Hide;
  WizardForm.WizardBitmapImage.Hide;
  
  // Create custom full-page static background image
  CustomWelcomeBg := TBitmapImage.Create(WizardForm);
  CustomWelcomeBg.Parent := WizardForm.WelcomePage;
  CustomWelcomeBg.Left := 0;
  CustomWelcomeBg.Top := 0;
  CustomWelcomeBg.Width := WizardForm.WelcomePage.Width;
  CustomWelcomeBg.Height := WizardForm.WelcomePage.Height;
  CustomWelcomeBg.Stretch := True;
  CustomWelcomeBg.Enabled := False; // Click-transparent
  
  if FileExists(ExpandConstant('{tmp}\wizard_welcome.bmp')) then
  begin
    CustomWelcomeBg.Bitmap.LoadFromFile(ExpandConstant('{tmp}\wizard_welcome.bmp'));
  end;
  
  // ----------------- APP LOGO on Welcome page only (top-left, above title) -----------------
  AppLogoImg := TBitmapImage.Create(WizardForm);
  AppLogoImg.Parent := WizardForm.WelcomePage;
  AppLogoImg.Left := ScaleX(60);
  AppLogoImg.Top := ScaleY(20);
  AppLogoImg.Width := ScaleX(70);
  AppLogoImg.Height := ScaleY(70);
  AppLogoImg.Stretch := True;
  AppLogoImg.Enabled := False; // Click-transparent
  if FileExists(ExpandConstant('{tmp}\app_logo.bmp')) then
  begin
    AppLogoImg.Bitmap.LoadFromFile(ExpandConstant('{tmp}\app_logo.bmp'));
  end;
  AppLogoImg.BringToFront;
  
  // Create custom overlay heading text
  CustomWelcomeTitle := TLabel.Create(WizardForm);
  CustomWelcomeTitle.Parent := WizardForm.WelcomePage;
  CustomWelcomeTitle.AutoSize := False;
  CustomWelcomeTitle.Left := ScaleX(60);
  CustomWelcomeTitle.Top := ScaleY(100);
  CustomWelcomeTitle.Width := ScaleX(380);
  CustomWelcomeTitle.Height := ScaleY(50);
  CustomWelcomeTitle.Font.Name := 'Segoe UI';
  CustomWelcomeTitle.Font.Size := 22;
  CustomWelcomeTitle.Font.Style := [fsBold];
  CustomWelcomeTitle.Font.Color := GoldColor;
  CustomWelcomeTitle.Caption := 'Welcome to PennyBook';
  CustomWelcomeTitle.Enabled := False; // Click-transparent
  
  // Create custom overlay description text
  CustomWelcomeDesc := TLabel.Create(WizardForm);
  CustomWelcomeDesc.Parent := WizardForm.WelcomePage;
  CustomWelcomeDesc.AutoSize := False;
  CustomWelcomeDesc.Left := ScaleX(60);
  CustomWelcomeDesc.Top := ScaleY(180);
  CustomWelcomeDesc.Width := ScaleX(380);
  CustomWelcomeDesc.Height := ScaleY(150);
  CustomWelcomeDesc.WordWrap := True;
  CustomWelcomeDesc.Font.Name := 'Segoe UI';
  CustomWelcomeDesc.Font.Size := 11;
  CustomWelcomeDesc.Font.Color := TxtColor;
  CustomWelcomeDesc.Caption := 'PennyBook is your premium personal finance ledger. Style your budgets, track your investments, and build your wealth.' + #13#10#13#10 + 'Click Next to begin the installation.';
  CustomWelcomeDesc.Enabled := False; // Click-transparent
  
  // ----------------- CREATE CUSTOM FINISHED PAGE -----------------
  // Hide standard Finished page text
  WizardForm.FinishedHeadingLabel.Hide;
  WizardForm.FinishedLabel.Hide;
  
  // Create custom full-page static background image
  CustomFinishedBg := TBitmapImage.Create(WizardForm);
  CustomFinishedBg.Parent := WizardForm.FinishedPage;
  CustomFinishedBg.Left := 0;
  CustomFinishedBg.Top := 0;
  CustomFinishedBg.Width := WizardForm.FinishedPage.Width;
  CustomFinishedBg.Height := WizardForm.FinishedPage.Height;
  CustomFinishedBg.Stretch := True;
  CustomFinishedBg.Enabled := False; // Click-transparent
  
  if FileExists(ExpandConstant('{tmp}\wizard_welcome.bmp')) then
  begin
    CustomFinishedBg.Bitmap.LoadFromFile(ExpandConstant('{tmp}\wizard_welcome.bmp'));
  end;
  
  // Create custom overlay heading text
  CustomFinishedTitle := TLabel.Create(WizardForm);
  CustomFinishedTitle.Parent := WizardForm.FinishedPage;
  CustomFinishedTitle.AutoSize := False;
  CustomFinishedTitle.Left := ScaleX(60);
  CustomFinishedTitle.Top := ScaleY(100);
  CustomFinishedTitle.Width := ScaleX(380);
  CustomFinishedTitle.Height := ScaleY(50);
  CustomFinishedTitle.Font.Name := 'Segoe UI';
  CustomFinishedTitle.Font.Size := 22;
  CustomFinishedTitle.Font.Style := [fsBold];
  CustomFinishedTitle.Font.Color := GoldColor;
  CustomFinishedTitle.Caption := 'Installation Completed';
  CustomFinishedTitle.Enabled := False; // Click-transparent
  
  // Create custom overlay description text
  CustomFinishedDesc := TLabel.Create(WizardForm);
  CustomFinishedDesc.Parent := WizardForm.FinishedPage;
  CustomFinishedDesc.AutoSize := False;
  CustomFinishedDesc.Left := ScaleX(60);
  CustomFinishedDesc.Top := ScaleY(180);
  CustomFinishedDesc.Width := ScaleX(380);
  CustomFinishedDesc.Height := ScaleY(80);
  CustomFinishedDesc.WordWrap := True;
  CustomFinishedDesc.Font.Name := 'Segoe UI';
  CustomFinishedDesc.Font.Size := 11;
  CustomFinishedDesc.Font.Color := TxtColor;
  CustomFinishedDesc.Caption := 'PennyBook has been successfully installed on your computer.' + #13#10#13#10 + 'You can run it from the Desktop or Start Menu.';
  CustomFinishedDesc.Enabled := False; // Click-transparent
  
  // Reposition the standard Run List check box to overlay cleanly (Parented to WizardForm so it stays active!)
  WizardForm.RunList.Parent := WizardForm;
  WizardForm.RunList.Left := ScaleX(60);
  WizardForm.RunList.Top := ScaleY(290);
  WizardForm.RunList.Width := ScaleX(380);
  WizardForm.RunList.Height := ScaleY(80);
  WizardForm.RunList.Color := BgColor;
  WizardForm.RunList.Font.Color := TxtColor;
  WizardForm.RunList.BorderStyle := bsNone;
  WizardForm.RunList.BringToFront;

  // ----------------- CUSTOM LAUNCHER CLOSE BUTTON (X) -----------------
  CloseLabel := TLabel.Create(WizardForm);
  CloseLabel.Parent := WizardForm;
  CloseLabel.Left := ScaleX(760);
  CloseLabel.Top := ScaleY(15);
  CloseLabel.Font.Name := 'Segoe UI';
  CloseLabel.Font.Size := 14;
  CloseLabel.Font.Style := [fsBold];
  CloseLabel.Font.Color := GoldColor;
  CloseLabel.Caption := 'X';
  CloseLabel.Cursor := crHand; // Pointer hand cursor
  CloseLabel.OnClick := @CloseLabelClick;
  CloseLabel.BringToFront;

  // ----------------- STYLING GENERAL CONTROLS -----------------
  // Customize fonts and colors for inner header text
  WizardForm.PageNameLabel.Font.Name := 'Segoe UI';
  WizardForm.PageNameLabel.Font.Color := GoldColor;
  WizardForm.PageNameLabel.Font.Style := [fsBold];
  WizardForm.PageDescriptionLabel.Font.Color := TxtColor;

  // Run recursive coloring for all other wizard pages
  ColorControls(WizardForm);
  
  // Explicitly apply overrides for parent controls that need special background colors
  WizardForm.MainPanel.Color := HeaderBgColor;
  WizardForm.PageNameLabel.Color := HeaderBgColor;
  WizardForm.PageDescriptionLabel.Color := HeaderBgColor;
  
  // Color the list boxes and memo specifically (Border removed for clean look)
  WizardForm.TasksList.Color := HeaderBgColor;
  WizardForm.TasksList.Font.Color := TxtColor;
  WizardForm.TasksList.BorderStyle := bsNone;
  
  WizardForm.ReadyMemo.Color := HeaderBgColor;
  WizardForm.ReadyMemo.Font.Color := TxtColor;
  
  // Style input edit boxes
  WizardForm.DirEdit.Color := HeaderBgColor;
  WizardForm.DirEdit.Font.Color := TxtColor;
  WizardForm.GroupEdit.Color := HeaderBgColor;
  WizardForm.GroupEdit.Font.Color := TxtColor;
  
  // Color the installation progress indicators
  WizardForm.StatusLabel.Font.Color := GoldColor;
  WizardForm.FilenameLabel.Font.Color := SubTextColor;

  // ----------------- REPOSITION STANDARD ACTION BUTTONS -----------------
  WizardForm.CancelButton.Left := ScaleX(680);
  WizardForm.CancelButton.Top := ScaleY(450);
  WizardForm.NextButton.Left := ScaleX(580);
  WizardForm.NextButton.Top := ScaleY(450);
  WizardForm.BackButton.Left := ScaleX(480);
  WizardForm.BackButton.Top := ScaleY(450);

  // Bring action buttons to the front so they are never clipped by notebooks/pages
  WizardForm.BackButton.BringToFront;
  WizardForm.NextButton.BringToFront;
  WizardForm.CancelButton.BringToFront;

  // ----------------- START TIMER FOR ANIMATION & DRAGGING -----------------
  TimerID := SetTimer(0, 0, 30, CreateCallback(@TimerCallback));
end;

procedure DeinitializeSetup();
var
  I: Integer;
begin
  // Clean up the timer to prevent resource leaks when the setup closes
  if TimerID <> 0 then
  begin
    KillTimer(0, TimerID);
  end;
end;
