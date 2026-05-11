param(
  [string]$ResultFile = ""
)

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

function Emit-Result {
  param(
    [string]$Status,
    [string]$Keywords,
    [string]$MaxNews,
    [string]$Theme
  )

  $lines = @(
    "STATUS=$Status",
    "KEYWORDS=$Keywords",
    "MAXNEWS=$MaxNews",
    "THEME=$Theme"
  )

  if ($ResultFile) {
    $dir = Split-Path -Path $ResultFile -Parent
    if ($dir) {
      New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    Set-Content -Path $ResultFile -Value $lines -Encoding Ascii
  }

  $lines | ForEach-Object { Write-Output $_ }
}

$keywords = @(
  "saneamento",
  "facilities",
  "aquisicao",
  "veiculos",
  "licitacao",
  "concessao",
  "ppp",
  "investimento",
  "expansao",
  "frota",
  "infraestrutura",
  "obras",
  "servicos terceirizados",
  "compras corporativas",
  "aquisicao de ativos",
  "novos contratos",
  "manutencao",
  "utilidades",
  "mobilidade operacional"
)

$form = New-Object System.Windows.Forms.Form
$form.Text = "Selecionar Parametros da Busca"
$form.Size = New-Object System.Drawing.Size(560, 650)
$form.StartPosition = "CenterScreen"
$form.TopMost = $true

$label = New-Object System.Windows.Forms.Label
$label.Text = "Escolha palavras-chave e quantidade de noticias desta execucao:"
$label.AutoSize = $true
$label.Location = New-Object System.Drawing.Point(14, 12)
$form.Controls.Add($label)

$cbSelectAll = New-Object System.Windows.Forms.CheckBox
$cbSelectAll.Text = "Selecionar todas as categorias"
$cbSelectAll.AutoSize = $true
$cbSelectAll.Location = New-Object System.Drawing.Point(16, 36)
$form.Controls.Add($cbSelectAll)

$checkList = New-Object System.Windows.Forms.CheckedListBox
$checkList.Location = New-Object System.Drawing.Point(16, 64)
$checkList.Size = New-Object System.Drawing.Size(510, 392)
$checkList.CheckOnClick = $true
foreach ($kw in $keywords) { [void]$checkList.Items.Add($kw) }
$form.Controls.Add($checkList)

$cbSelectAll.Add_CheckedChanged({
  for ($i = 0; $i -lt $checkList.Items.Count; $i++) {
    $checkList.SetItemChecked($i, $cbSelectAll.Checked)
  }
})

$cbKeepQty = New-Object System.Windows.Forms.CheckBox
$cbKeepQty.Text = "Manter quantidade padrao do config"
$cbKeepQty.Checked = $true
$cbKeepQty.AutoSize = $true
$cbKeepQty.Location = New-Object System.Drawing.Point(16, 468)
$form.Controls.Add($cbKeepQty)

$lblQty = New-Object System.Windows.Forms.Label
$lblQty.Text = "Quantidade maxima de noticias:"
$lblQty.AutoSize = $true
$lblQty.Location = New-Object System.Drawing.Point(16, 498)
$form.Controls.Add($lblQty)

$numQty = New-Object System.Windows.Forms.NumericUpDown
$numQty.Minimum = 1
$numQty.Maximum = 200
$numQty.Value = 50
$numQty.Enabled = $false
$numQty.Location = New-Object System.Drawing.Point(250, 494)
$numQty.Size = New-Object System.Drawing.Size(90, 24)
$form.Controls.Add($numQty)

$cbKeepQty.Add_CheckedChanged({
  $numQty.Enabled = -not $cbKeepQty.Checked
})

$lblTheme = New-Object System.Windows.Forms.Label
$lblTheme.Text = "Tema visual do relatorio:"
$lblTheme.AutoSize = $true
$lblTheme.Location = New-Object System.Drawing.Point(360, 498)
$form.Controls.Add($lblTheme)

$cmbTheme = New-Object System.Windows.Forms.ComboBox
$cmbTheme.DropDownStyle = 'DropDownList'
[void]$cmbTheme.Items.Add("light")
[void]$cmbTheme.Items.Add("dark_exec")
[void]$cmbTheme.Items.Add("boardroom_print")
$cmbTheme.SelectedIndex = 0
$cmbTheme.Location = New-Object System.Drawing.Point(362, 522)
$cmbTheme.Size = New-Object System.Drawing.Size(164, 24)
$form.Controls.Add($cmbTheme)

$btnKeep = New-Object System.Windows.Forms.Button
$btnKeep.Text = "Manter como esta"
$btnKeep.Location = New-Object System.Drawing.Point(16, 538)
$btnKeep.Size = New-Object System.Drawing.Size(145, 32)
$btnKeep.Add_Click({
  Emit-Result -Status "KEEP" -Keywords "__KEEP__" -MaxNews "__KEEP__" -Theme "__KEEP__"
  $form.Close()
})
$form.Controls.Add($btnKeep)

$btnApply = New-Object System.Windows.Forms.Button
$btnApply.Text = "Processar selecao"
$btnApply.Location = New-Object System.Drawing.Point(170, 538)
$btnApply.Size = New-Object System.Drawing.Size(145, 32)
$btnApply.Add_Click({
  $selected = @()
  foreach ($item in $checkList.CheckedItems) { $selected += $item.ToString() }
  $kwOut = if ($selected.Count -eq 0) { "__KEEP__" } else { ($selected -join ",") }
  $qtyOut = if ($cbKeepQty.Checked) { "__KEEP__" } else { [string]$numQty.Value }

  Emit-Result -Status "APPLY" -Keywords $kwOut -MaxNews $qtyOut -Theme ($cmbTheme.SelectedItem.ToString())
  $form.Close()
})
$form.Controls.Add($btnApply)

$btnCancel = New-Object System.Windows.Forms.Button
$btnCancel.Text = "Cancelar"
$btnCancel.Location = New-Object System.Drawing.Point(322, 538)
$btnCancel.Size = New-Object System.Drawing.Size(90, 32)
$btnCancel.Add_Click({
  Emit-Result -Status "CANCEL" -Keywords "__KEEP__" -MaxNews "__KEEP__" -Theme "__KEEP__"
  $form.Close()
})
$form.Controls.Add($btnCancel)

[void]$form.ShowDialog()
