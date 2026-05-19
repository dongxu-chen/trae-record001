# SDK 使用说明

## Go SDK

### 安装

```bash
go get github.com/yourusername/idgenerator
```

### 快速开始

```go
package main

import (
    "fmt"
    "log"
    "github.com/yourusername/idgenerator"
)

func main() {
    client := idgenerator.NewClient("http://localhost:3000")
    
    // 生成单个ID
    resp, err := client.NextID("order", true)
    if err != nil {
        log.Fatal(err)
    }
    fmt.Printf("ID: %s\n", resp.ID)
    fmt.Printf("格式化ID: %s\n", resp.FormattedID)
    
    // 批量生成ID
    batch, err := client.Batch(10, "user", false)
    if err != nil {
        log.Fatal(err)
    }
    fmt.Printf("批量生成了 %d 个ID\n", batch.Count)
    
    // 解析ID
    parsed, err := client.Parse("1234567890123456789")
    if err != nil {
        log.Fatal(err)
    }
    fmt.Printf("Worker ID: %d\n", parsed.Data.Snowflake.WorkerID)
    
    // 获取Worker容量
    capacity, err := client.GetWorkerCapacity()
    if err != nil {
        log.Fatal(err)
    }
    fmt.Printf("当前容量: %d/%d\n", capacity.Data.Current, capacity.Data.Max)
    
    // 扩容Worker
    result, err := client.ExpandWorkerCapacity(512)
    if err != nil {
        log.Fatal(err)
    }
    fmt.Printf("扩容后容量: %d\n", result.Data.Current)
    
    // 性能压测
    benchmark, err := client.Benchmark(10000, "snowflake")
    if err != nil {
        log.Fatal(err)
    }
    fmt.Printf("吞吐量: %d ops/s\n", benchmark.Benchmark.ThroughputPerSecond)
}
```

### API 方法

| 方法 | 说明 |
|------|------|
| `NextID(bizType string, format bool)` | 生成雪花ID |
| `NextSegmentID(bizType string, format bool, step int)` | 生成号段ID |
| `Batch(count int, bizType string, format bool)` | 批量生成ID |
| `Parse(id string)` | 解析ID信息 |
| `GetSegmentStatus(bizType string)` | 获取号段状态 |
| `GetWorkerCapacity()` | 获取Worker容量 |
| `ExpandWorkerCapacity(targetCount int)` | 扩容Worker数量 |
| `Benchmark(count int, idType string)` | 性能压测 |

---

## Java SDK

### 安装

Maven 依赖:

```xml
<dependency>
    <groupId>com.idgenerator</groupId>
    <artifactId>id-generator-client</artifactId>
    <version>1.0.0</version>
</dependency>
```

### 快速开始

```java
package com.example;

import com.idgenerator.IdGeneratorClient;
import com.idgenerator.IdGeneratorClient.IDResponse;
import com.idgenerator.IdGeneratorClient.BatchResponse;
import com.idgenerator.IdGeneratorClient.ParseResponse;
import com.idgenerator.IdGeneratorClient.WorkerCapacityResponse;
import com.idgenerator.IdGeneratorClient.BenchmarkResponse;

public class Main {
    public static void main(String[] args) throws Exception {
        IdGeneratorClient client = new IdGeneratorClient("http://localhost:3000");
        
        // 生成单个ID
        IDResponse resp = client.nextID("order", true);
        System.out.println("ID: " + resp.id);
        System.out.println("格式化ID: " + resp.formattedId);
        
        // 批量生成ID
        BatchResponse batch = client.batch(10, "user", false);
        System.out.println("批量生成了 " + batch.count + " 个ID");
        
        // 解析ID
        ParseResponse parsed = client.parse("1234567890123456789");
        System.out.println("Worker ID: " + parsed.data.snowflake.workerId);
        
        // 获取Worker容量
        WorkerCapacityResponse capacity = client.getWorkerCapacity();
        System.out.println("当前容量: " + capacity.data.current + "/" + capacity.data.max);
        
        // 扩容Worker
        WorkerCapacityResponse result = client.expandWorkerCapacity(512);
        System.out.println("扩容后容量: " + result.data.current);
        
        // 性能压测
        BenchmarkResponse benchmark = client.benchmark(10000, "snowflake");
        System.out.println("吞吐量: " + benchmark.benchmark.throughputPerSecond + " ops/s");
    }
}
```

### API 方法

| 方法 | 说明 |
|------|------|
| `nextId()` | 生成雪花ID |
| `nextId(String bizType, boolean format)` | 带业务类型和格式化选项生成ID |
| `nextSegmentId(String bizType, boolean format, int step)` | 生成号段ID |
| `batch(int count, String bizType, boolean format)` | 批量生成ID |
| `parse(String id)` | 解析ID信息 |
| `getWorkerCapacity()` | 获取Worker容量 |
| `expandWorkerCapacity(int targetCount)` | 扩容Worker数量 |
| `benchmark(int count, String type)` | 性能压测 |