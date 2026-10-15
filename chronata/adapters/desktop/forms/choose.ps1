$script:picked = $null

foreach ($option in $env:CHRONATA_OPTIONS -split "`n") {
    $button = New-Object Windows.Forms.Button
    $button.Text = $option
    $button.UseMnemonic = $false
    $button.AutoSize = $true
    $button.MinimumSize = New-Object Drawing.Size 360, 0
    $button.Add_Click({ $script:picked = $this.Text; $form.Close() })
    $layout.Controls.Add($button)
}

$cancel = New-Object Windows.Forms.Button
$cancel.Text = 'Cancel'
$cancel.DialogResult = 'Cancel'
$cancel.MinimumSize = New-Object Drawing.Size 360, 0
$layout.Controls.Add($cancel)
$form.CancelButton = $cancel
$form.Add_Shown({ $form.Activate() })

[void]$form.ShowDialog()
if ($null -eq $script:picked) { exit 1 }
[Console]::Out.Write($script:picked)
