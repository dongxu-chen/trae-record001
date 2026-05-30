#!/bin/bash

BACKEND_URL="http://localhost:8080"

echo "Injecting demo flow data..."

flows=(
    '{"sourceName":"frontend-abc123","sourceNamespace":"default","destName":"backend-def456","destNamespace":"default","protocol":"TCP","port":8080,"count":100}'
    '{"sourceName":"backend-def456","sourceNamespace":"default","destName":"database-ghi789","destNamespace":"default","protocol":"TCP","port":5432,"count":75}'
    '{"sourceName":"frontend-abc123","sourceNamespace":"default","destName":"redis-jkl012","destNamespace":"default","protocol":"TCP","port":6379,"count":50}'
    '{"sourceName":"backend-def456","sourceNamespace":"default","destName":"cache-mno345","destNamespace":"default","protocol":"UDP","port":53,"count":200}'
    '{"sourceName":"monitoring-pqr678","sourceNamespace":"monitoring","destName":"backend-def456","destNamespace":"default","protocol":"TCP","port":9090,"count":30}'
)

for flow in "${flows[@]}"; do
    curl -X POST "$BACKEND_URL/api/flows" \
        -H "Content-Type: application/json" \
        -d "$flow"
    echo ""
done

echo ""
echo "Demo flow data injected successfully!"
echo ""
echo "Pods:"
curl -s "$BACKEND_URL/api/topology" | jq '.pods'
echo ""
echo "Flows:"
curl -s "$BACKEND_URL/api/topology" | jq '.flows'
