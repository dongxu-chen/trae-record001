# PowerShell 示例脚本 - 创建任务

$BASE_URL = "http://localhost:8080/api/v1"

Write-Host "=== 创建 Cron 任务 ===" -ForegroundColor Green
$cronTask = @{
    name = "每分钟日志任务"
    description = "每分钟执行一次的日志记录任务"
    task_type = "log"
    payload = '{"message": "Cron任务执行了", "level": "INFO"}'
    trigger_type = "cron"
    cron_expr = "0 * * * * *"
    max_retries = 3
    retry_delay = 5
} | ConvertTo-Json

Invoke-RestMethod -Uri "$BASE_URL/tasks" -Method Post -Body $cronTask -ContentType "application/json" | ConvertTo-Json -Depth 10

Write-Host "`n=== 创建间隔任务 ===" -ForegroundColor Green
$intervalTask = @{
    name = "每30秒间隔任务"
    description = "每30秒执行一次的间隔任务"
    task_type = "log"
    payload = '{"message": "间隔任务执行了", "level": "DEBUG"}'
    trigger_type = "interval"
    interval_sec = 30
    max_retries = 2
    retry_delay = 10
} | ConvertTo-Json

Invoke-RestMethod -Uri "$BASE_URL/tasks" -Method Post -Body $intervalTask -ContentType "application/json" | ConvertTo-Json -Depth 10

Write-Host "`n=== 创建任务 A (前置任务) ===" -ForegroundColor Green
$taskA = @{
    name = "任务A - 前置任务"
    description = "任务链中的第一个任务"
    task_type = "log"
    payload = '{"message": "任务A执行完成", "level": "INFO"}'
    trigger_type = "manual"
    max_retries = 3
} | ConvertTo-Json

$taskAResult = Invoke-RestMethod -Uri "$BASE_URL/tasks" -Method Post -Body $taskA -ContentType "application/json"
$taskAId = $taskAResult.id
Write-Host "任务 A ID: $taskAId" -ForegroundColor Cyan
$taskAResult | ConvertTo-Json -Depth 10

Write-Host "`n=== 创建任务 B (依赖任务 A) ===" -ForegroundColor Green
$taskB = @{
    name = "任务B - 依赖任务A"
    description = "任务A完成后自动触发"
    task_type = "log"
    payload = '{"message": "任务B执行了 - 任务A已完成", "level": "INFO"}'
    trigger_type = "manual"
    dependencies = $taskAId
    max_retries = 3
} | ConvertTo-Json

Invoke-RestMethod -Uri "$BASE_URL/tasks" -Method Post -Body $taskB -ContentType "application/json" | ConvertTo-Json -Depth 10

Write-Host "`n=== 获取所有任务列表 ===" -ForegroundColor Green
Invoke-RestMethod -Uri "$BASE_URL/tasks?limit=10" | ConvertTo-Json -Depth 10

Write-Host "`n=== 触发任务 A (将同时触发任务 B) ===" -ForegroundColor Yellow
Write-Host "运行以下命令手动触发任务 A:"
Write-Host "Invoke-RestMethod -Uri `"$BASE_URL/tasks/$taskAId/trigger`" -Method Post"
