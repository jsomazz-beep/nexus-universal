param(
  [string]$TaskName = "WeeklyNewsReporter",
  [string]$PythonExe = "python",
  [string]$ProjectPath = "C:\Users\zigur\OneDrive\Documentos\New project\weekly_news_reporter",
  [string]$RunDay = "MON",
  [string]$RunTime = "08:00"
)

$ErrorActionPreference = "Stop"

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File \"$ProjectPath\scripts\run_weekly.ps1\" -PythonExe \"$PythonExe\""
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $RunDay -At $RunTime
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2) -RestartCount 2 -RestartInterval (New-TimeSpan -Minutes 5)

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description "Geração semanal automatizada de relatório de notícias e oportunidades" -Force

Write-Host "Task agendada com sucesso: $TaskName"
