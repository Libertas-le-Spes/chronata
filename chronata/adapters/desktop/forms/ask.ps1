$answer = New-Object Windows.Forms.TextBox
$answer.Text = $env:CHRONATA_SUGGESTED
$answer.Width = 360
$layout.Controls.Add($answer)

$buttons = New-Object Windows.Forms.FlowLayoutPanel
$buttons.AutoSize = $true
$ok = New-Object Windows.Forms.Button
$ok.Text = 'OK'
$ok.DialogResult = 'OK'
$cancel = New-Object Windows.Forms.Button
$cancel.Text = 'Cancel'
$cancel.DialogResult = 'Cancel'
$buttons.Controls.AddRange(@($ok, $cancel))
$layout.Controls.Add($buttons)

$form.AcceptButton = $ok
$form.CancelButton = $cancel
$form.Add_Shown({ $form.Activate(); $answer.SelectAll(); $answer.Focus() })

if ($form.ShowDialog() -ne 'OK') { exit 1 }
[Console]::Out.Write($answer.Text)
