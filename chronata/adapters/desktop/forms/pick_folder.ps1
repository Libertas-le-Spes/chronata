Add-Type -AssemblyName System.Windows.Forms
[Console]::OutputEncoding = New-Object Text.UTF8Encoding $false

$owner = New-Object Windows.Forms.Form
$owner.TopMost = $true
$picker = New-Object Windows.Forms.FolderBrowserDialog
$picker.Description = $env:CHRONATA_TITLE
$picker.ShowNewFolderButton = $true

if ($picker.ShowDialog($owner) -ne 'OK') { exit 1 }
[Console]::Out.Write($picker.SelectedPath)
