$BACKEND_URL = "http://localhost:8080"

Write-Host "Injecting demo flow data..." -ForegroundColor Green

$flows = @(
    '{"sourceName":"frontend-abc123","sourceNamespace":"default","destName":"backend-def456","destNamespace":"default","protocol":"TCP","port":8080,"count":100}',
    '{"sourceName":"backend-def456","sourceNamespace":"default","destName":"database-ghi789","destNamespace":"default","protocol":"TCP","port":5432,"count":75}',
    '{"sourceName":"frontend-abc123","sourceNamespace":"default","destName":"redis-jkl012","destNamespace":"default","protocol":"TCP","port":6379,"count":50}',
    '{"sourceName":"backend-def456","sourceNamespace":"default","destName":"cache-mno345","destNamespace":"default","protocol":"UDP","port":53,"count":200}',
    '{"sourceName":"monitoring-pqr678","sourceNamespace":"monitoring","destName":"backend-def456","destNamespace":"default","protocol":"TCP","port":9090,"count":30}'
)

foreach ($flow in $flows) {
    Invoke-RestMethod -Method Post -Uri "$BACKEND_URL/api/flows" -Body $flow -ContentType "application/json"
}

Write-Host ""
Write-Host "Demo flow data injected successfully!" -ForegroundColor Green
