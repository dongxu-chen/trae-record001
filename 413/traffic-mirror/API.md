# Traffic Mirror Service Mesh Tool - API Specification

## Overview

The Traffic Mirror tool provides a REST API for managing traffic mirroring configuration
and querying comparison results between production and test environments.

**Base URL:** `http://<control-plane-host>:8080/api/v1`

---

## Key Architecture Features

### 1. Distributed Consistent Hash Sampling
Instead of random sampling, the Wasm plugin uses **FNV-64a consistent hashing** on a composite key:
- Primary key: the header specified by `sampling_hash_key` (default: `x-request-id`)
- Fallback: `method|path|authority`
- Decision: `FNV64a(key) % 10000 < samplingRate * 10000`
- **Guarantee**: Same request key → same hash → same mirror decision across all Envoy instances

### 2. TLS Termination at Sidecar
HTTPS traffic is **decrypted at the Envoy Sidecar** before the Wasm filter processes it:
- Port 10000: HTTPS listener (TLS terminated)
- Port 10001: HTTP listener (for non-TLS traffic)
- Both share the same Wasm filter chain
- Upstream connections to production/test services also use mTLS

### 3. Protobuf Dynamic Reflection
- Wasm plugin: wire-format field-level comparison (field number, wire type, value)
- Control plane: full protobuf descriptor-based dynamic message comparison
- Register `.proto` file descriptors via the Proto Schema API

---

## Endpoints

### 1. Configuration Management

#### GET /api/v1/config
Get current mirror configuration.

**Response:**
```json
{
  "sampling_rate": 0.1,
  "sampling_hash_key": "x-request-id",
  "header_rules": [...],
  "test_cluster": "test_service",
  "control_plane": "control-plane:8080",
  "enabled": true,
  "proto_content_types": ["application/grpc", "application/grpc+proto", "application/x-protobuf", "application/protobuf"]
}
```

---

#### PUT /api/v1/config/sampling-rate
Update traffic sampling rate.

**Request:**
```json
{ "rate": 0.5 }
```

**Response:**
```json
{ "message": "sampling rate updated", "rate": 0.5 }
```

**Constraints:** `rate` must be between 0.0 and 1.0

---

#### PUT /api/v1/config/sampling-hash-key
Update the header key used for consistent hashing.

**Request:**
```json
{ "hash_key": "x-trace-id" }
```

**Response:**
```json
{ "message": "sampling hash key updated", "hash_key": "x-trace-id" }
```

**Note:** The hash key determines request identity for consistent sampling. Use a globally unique ID like `x-request-id` or `x-trace-id`.

---

#### PUT /api/v1/config/test-cluster
Update test cluster name.

**Request:**
```json
{ "cluster": "test_service_v2" }
```

**Response:**
```json
{ "message": "test cluster updated", "cluster": "test_service_v2" }
```

---

#### PUT /api/v1/config/enabled
Enable or disable traffic mirroring.

**Request:**
```json
{ "enabled": false }
```

**Response:**
```json
{ "message": "mirror status updated", "enabled": false }
```

---

### 2. Header Rules

#### GET /api/v1/header-rules
List all header modification rules.

**Response:**
```json
[
  {
    "id": 1,
    "name": "x-env",
    "value": "production",
    "operation": "add",
    "match": "",
    "override": true,
    "priority": 0,
    "enabled": true
  }
]
```

**Operations:**
- `add` - Add a header (optionally override existing)
- `remove` - Remove a header
- `replace` - Replace a header value (requires `match` field)
- `rename` - Rename a header

---

#### POST /api/v1/header-rules
Create a new header rule.

**Request:**
```json
{
  "name": "x-env",
  "value": "production",
  "operation": "add",
  "override": true
}
```

**Response:**
```json
{
  "id": 2,
  "name": "x-env",
  "value": "production",
  "operation": "add",
  "override": true,
  "priority": 0,
  "enabled": true
}
```

---

#### GET /api/v1/header-rules/:id
Get a specific header rule.

---

#### PUT /api/v1/header-rules/:id
Update a header rule.

---

#### DELETE /api/v1/header-rules/:id
Delete a header rule.

---

### 3. Proto Schema Management

#### GET /api/v1/proto-schemas
List all registered proto schemas.

**Response:**
```json
[
  {
    "id": 1,
    "message_type": "user.User",
    "proto_file_name": "user.proto",
    "package_name": "user",
    "service_name": "UserService",
    "method_name": "GetUser",
    "description": "User service proto",
    "enabled": true
  }
]
```

---

#### POST /api/v1/proto-schemas
Register a new proto schema.

**Request:**
```json
{
  "message_type": "user.User",
  "proto_file_name": "user.proto",
  "file_descriptor": "<base64-encoded FileDescriptorProto>",
  "package_name": "user",
  "service_name": "UserService",
  "method_name": "GetUser",
  "description": "User service proto"
}
```

**Response:**
```json
{
  "id": 2,
  "message_type": "user.User",
  "proto_file_name": "user.proto",
  "package_name": "user",
  "service_name": "UserService",
  "method_name": "GetUser",
  "description": "User service proto",
  "enabled": true
}
```

**File Descriptor Generation:**
```bash
# Generate FileDescriptorProto from .proto file
protoc --descriptor_set_out=user.desc user.proto
# Then base64 encode the file:
base64 user.desc
```

---

#### GET /api/v1/proto-schemas/:id
Get a specific proto schema.

---

#### GET /api/v1/proto-schemas/by-message-type/:message_type
Get a proto schema by message type (e.g., `user.User`).

---

#### PUT /api/v1/proto-schemas/:id
Update a proto schema.

---

#### DELETE /api/v1/proto-schemas/:id
Delete a proto schema.

---

### 4. Comparison Results

#### GET /api/v1/comparisons
Query comparison results.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | string | Filter by request path (partial match) |
| `method` | string | Filter by HTTP method |
| `severity` | string | Filter by severity: `critical`, `warning`, `info` |
| `has_diff` | bool | Filter by whether differences exist |
| `is_proto` | bool | Filter by protobuf messages |
| `start_time` | int64 | Unix nanoseconds timestamp start |
| `end_time` | int64 | Unix nanoseconds timestamp end |
| `page` | int | Page number (default: 1) |
| `page_size` | int | Items per page (default: 20, max: 100) |

**Example:** `GET /api/v1/comparisons?severity=critical&has_diff=true&is_proto=true`

**Response:**
```json
{
  "results": [
    {
      "id": 123,
      "request_id": "abc-123",
      "timestamp": 1700000000000000000,
      "path": "/api/users/1",
      "method": "GET",
      "prod_status": 200,
      "test_status": 200,
      "status_match": true,
      "body_match": false,
      "has_diff": true,
      "severity": "warning",
      "is_proto": true,
      "proto_message_type": "user.UserResponse",
      "differences": [
        {
          "field": "email",
          "type": "json_field",
          "prod_value": "alice@example.com",
          "test_value": "alice@test.example.com",
          "severity": "warning"
        },
        {
          "field": "proto_field_2",
          "type": "proto",
          "prod_value": "varint:1",
          "test_value": "varint:2",
          "severity": "warning"
        }
      ],
      "proto_differences": [
        {
          "field_number": 2,
          "wire_type": 0,
          "prod_value": "varint:1",
          "test_value": "varint:2",
          "severity": "warning"
        }
      ]
    }
  ],
  "total": 150,
  "page": 1,
  "page_size": 50
}
```

---

#### GET /api/v1/comparisons/:id
Get a specific comparison result.

---

#### GET /api/v1/comparisons/stats
Get comparison statistics.

**Response:**
```json
{
  "total_count": 1500,
  "match_count": 1200,
  "mismatch_count": 300,
  "proto_count": 450,
  "severity_count": {
    "critical": 25,
    "warning": 150,
    "info": 125
  },
  "top_diffs": [
    {
      "path": "/api/users/:id",
      "count": 45,
      "severity": "warning"
    }
  ],
  "top_proto_diffs": [
    {
      "path": "/grpc/user.User/GetUser",
      "count": 20,
      "severity": "critical"
    }
  ]
}
```

---

### 5. System Status

#### GET /api/v1/status
Get mirror system status.

**Response:**
```json
{
  "enabled": true,
  "sampling_rate": 0.1,
  "sampling_hash_key": "x-request-id",
  "total_requests": 1500,
  "mirrored_count": 150,
  "test_cluster": "test_service",
  "proto_schema_count": 5
}
```

---

#### GET /health
Health check endpoint.

**Response:**
```json
{ "status": "ok" }
```

---

#### GET /metrics
Prometheus metrics endpoint.

---

## Severity Levels

| Level      | Description                                      |
|------------|--------------------------------------------------|
| `critical` | Significant behavioral differences detected       |
| `warning`  | Minor differences or edge cases                  |
| `info`     | Informational differences (e.g., timestamps)     |
| `none`     | No differences detected                          |

## Error Responses

| Code | Description           |
|------|-----------------------|
| 200  | Success               |
| 201  | Resource created      |
| 400  | Invalid request       |
| 404  | Resource not found    |
| 500  | Internal server error  |

Error response format:
```json
{ "error": "Description of the error" }
```

---

## Usage Examples

### Configure Consistent Hash Sampling

```bash
# Set sampling rate to 50%
curl -X PUT http://localhost:8080/api/v1/config/sampling-rate \
  -H "Content-Type: application/json" \
  -d '{"rate": 0.5}'

# Use x-trace-id as the hash key for consistent sampling
curl -X PUT http://localhost:8080/api/v1/config/sampling-hash-key \
  -H "Content-Type: application/json" \
  -d '{"hash_key": "x-trace-id"}'
```

### Register a Proto Schema

```bash
# Generate FileDescriptorProto
protoc --descriptor_set_out=/tmp/user.desc --include_imports api/user.proto
FD_BASE64=$(base64 /tmp/user.desc)

# Register
curl -X POST http://localhost:8080/api/v1/proto-schemas \
  -H "Content-Type: application/json" \
  -d "{
    \"message_type\": \"user.User\",
    \"proto_file_name\": \"user.proto\",
    \"file_descriptor\": \"${FD_BASE64}\",
    \"package_name\": \"user\",
    \"service_name\": \"UserService\",
    \"description\": \"User service proto\"
  }"
```

### Query Critical Proto Differences

```bash
curl "http://localhost:8080/api/v1/comparisons?severity=critical&has_diff=true&is_proto=true"
```

### Add Header Rule for gRPC Traffic

```bash
# Add x-env header to mark mirrored gRPC requests
curl -X POST http://localhost:8080/api/v1/header-rules \
  -H "Content-Type: application/json" \
  -d '{"name": "x-env", "value": "staging", "operation": "add", "override": true}'
```

---

## Ports Reference

| Port    | Service            | Protocol | Description                          |
|---------|--------------------|----------|--------------------------------------|
| 10000   | Envoy Sidecar      | HTTPS    | TLS-terminated HTTPS traffic          |
| 10001   | Envoy Sidecar      | HTTP     | Plain HTTP traffic                    |
| 15000   | Envoy Admin        | HTTP     | Envoy admin UI and stats             |
| 8080    | Control Plane      | HTTP     | REST API and management              |
| 18000   | Control Plane      | gRPC     | xDS configuration protocol           |
| 16686   | Jaeger UI          | HTTP     | Distributed tracing UI               |
| 4317    | Jaeger OTLP        | gRPC     | OpenTelemetry trace receiver         |
