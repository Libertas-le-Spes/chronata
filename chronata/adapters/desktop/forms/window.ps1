Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[Windows.Forms.Application]::EnableVisualStyles()
[Console]::OutputEncoding = New-Object Text.UTF8Encoding $false

$form = New-Object Windows.Forms.Form
$form.Text = $env:CHRONATA_TITLE
$form.TopMost = $true
$form.StartPosition = 'CenterScreen'
$form.FormBorderStyle = 'FixedDialog'
$form.MaximizeBox = $false
$form.MinimizeBox = $false
$form.AutoSize = $true
$form.AutoSizeMode = 'GrowAndShrink'

$layout = New-Object Windows.Forms.FlowLayoutPanel
$layout.FlowDirection = 'TopDown'
$layout.WrapContents = $false
$layout.AutoSize = $true
$layout.Padding = New-Object Windows.Forms.Padding 12
$form.Controls.Add($layout)

$question = New-Object Windows.Forms.Label
$question.Text = $env:CHRONATA_QUESTION
$question.UseMnemonic = $false
$question.AutoSize = $true
$question.MaximumSize = New-Object Drawing.Size 360, 0
$layout.Controls.Add($question)
