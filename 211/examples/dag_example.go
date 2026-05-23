//go:build ignore

package main

import (
	"fmt"
	"log"

	"scheduler/pkg/dag"
	"scheduler/pkg/retry"
	"scheduler/internal/store"
	"time"
)

func main() {
	fmt.Println("=== DAG 拓扑排序示例 ===")
	testDAG()

	fmt.Println("\n=== 指数退避算法示例 ===")
	testExponentialBackoff()

	fmt.Println("\n=== 按月分表示例 ===")
	testPartitioning()
}

func testDAG() {
	graph := dag.NewTaskDependencyGraph()

	tasks := map[string][]string{
		"task_a": {},
		"task_b": {"task_a"},
		"task_c": {"task_a"},
		"task_d": {"task_b", "task_c"},
		"task_e": {"task_d"},
		"task_f": {"task_e"},
		"task_g": {"task_f"},
		"task_h": {"task_g"},
		"task_i": {"task_h"},
		"task_j": {"task_i"},
		"task_k": {"task_j"},
	}

	for taskID, deps := range tasks {
		if err := graph.AddTask(taskID, deps, nil); err != nil {
			log.Fatalf("Failed to add task %s: %v", taskID, err)
		}
	}

	fmt.Printf("DAG 节点数: %d\n", graph.NodeCount())
	fmt.Printf("DAG 边数: %d\n", graph.EdgeCount())

	order, err := graph.GetExecutionOrder()
	if err != nil {
		log.Fatalf("Topological sort failed: %v", err)
	}

	fmt.Println("执行顺序:")
	for i, taskID := range order {
		fmt.Printf("  %d. %s\n", i+1, taskID)
	}

	completed := map[string]bool{"task_a": true}
	readyTasks := graph.GetReadyTasks(completed)
	fmt.Println("任务A完成后可执行的任务:", readyTasks)
}

func testExponentialBackoff() {
	config := retry.DefaultConfig()
	fmt.Printf("默认配置: 最大重试=%d, 基数=%.1f, 最大延迟=%v\n",
		config.MaxAttempts, config.Multiplier, config.MaxDelay)

	sequence := retry.GetBackoffSequence(5, 1*time.Second)
	fmt.Println("退避序列 (基础延迟1秒):")
	for i, delay := range sequence {
		fmt.Printf("  第%d次重试: %v\n", i+1, delay)
	}

	fmt.Println("\n计算下次重试时间:")
	for i := 0; i < 5; i++ {
		nextTime := retry.CalculateNextRetryTime(i, 5)
		fmt.Printf("  第%d次重试后: %v\n", i, nextTime.Format("15:04:05"))
	}
}

func testPartitioning() {
	now := time.Now()
	fmt.Println("当前时间:", now.Format("2006-01-02 15:04:05"))
	fmt.Println("当前分表:", store.GetCurrentPartitionTable())
	fmt.Println("上月分表:", store.GetPartitionTable(now.AddDate(0, -1, 0)))
	fmt.Println("下月分表:", store.GetPartitionTable(now.AddDate(0, 1, 0)))

	start := now.AddDate(0, -2, 0)
	end := now.AddDate(0, 1, 0)
	tables := store.GetPartitionTablesInRange(start, end)
	fmt.Println("\n时间范围内的分表:")
	for _, table := range tables {
		fmt.Println("  -", table)
	}
}
