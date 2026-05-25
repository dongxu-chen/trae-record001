package dag

import (
	"fmt"
	"math"
	"sort"
	"time"
)

type CriticalPathInfo struct {
	Path          []string
	TotalDuration time.Duration
}

type TaskScheduleInfo struct {
	TaskID          string
	EarliestStart   time.Duration
	EarliestFinish  time.Duration
	LatestStart     time.Duration
	LatestFinish    time.Duration
	Slack           time.Duration
	IsCritical      bool
}

func (d *DAG) CalculateCriticalPath() (*CriticalPathInfo, map[string]*TaskScheduleInfo, error) {
	topoOrder, err := d.GetTopoOrder()
	if err != nil {
		return nil, nil, err
	}

	scheduleInfo := d.calculateEarliestTimes(topoOrder)

	d.calculateLatestTimes(topoOrder, scheduleInfo)

	for _, info := range scheduleInfo {
		info.Slack = info.LatestStart - info.EarliestStart
		info.IsCritical = info.Slack == 0
	}

	criticalPath := d.findCriticalPath(topoOrder, scheduleInfo)

	var totalDuration time.Duration
	if len(criticalPath) > 0 {
		lastTaskID := criticalPath[len(criticalPath)-1]
		totalDuration = scheduleInfo[lastTaskID].EarliestFinish
	}

	return &CriticalPathInfo{
		Path:          criticalPath,
		TotalDuration: totalDuration,
	}, scheduleInfo, nil
}

func (d *DAG) calculateEarliestTimes(topoOrder []string) map[string]*TaskScheduleInfo {
	info := make(map[string]*TaskScheduleInfo)

	for _, taskID := range topoOrder {
		node := d.Nodes[taskID]
		task := node.Task

		var earliestStart time.Duration = 0
		for _, inNode := range node.InEdges {
			inInfo := info[inNode.Task.ID]
			if inInfo.EarliestFinish > earliestStart {
				earliestStart = inInfo.EarliestFinish
			}
		}

		duration := task.EstimatedTime
		if duration == 0 {
			duration = 1 * time.Minute
		}

		info[taskID] = &TaskScheduleInfo{
			TaskID:         taskID,
			EarliestStart:  earliestStart,
			EarliestFinish: earliestStart + duration,
		}
	}

	return info
}

func (d *DAG) calculateLatestTimes(topoOrder []string, info map[string]*TaskScheduleInfo) {
	var maxFinish time.Duration
	for _, taskInfo := range info {
		if taskInfo.EarliestFinish > maxFinish {
			maxFinish = taskInfo.EarliestFinish
		}
	}

	for i := len(topoOrder) - 1; i >= 0; i-- {
		taskID := topoOrder[i]
		node := d.Nodes[taskID]
		task := node.Task

		var latestFinish time.Duration = maxFinish
		for _, outNode := range node.OutEdges {
			outInfo := info[outNode.Task.ID]
			if outInfo.LatestStart < latestFinish {
				latestFinish = outInfo.LatestStart
			}
		}

		duration := task.EstimatedTime
		if duration == 0 {
			duration = 1 * time.Minute
		}

		taskInfo := info[taskID]
		taskInfo.LatestFinish = latestFinish
		taskInfo.LatestStart = latestFinish - duration
	}
}

func (d *DAG) findCriticalPath(topoOrder []string, info map[string]*TaskScheduleInfo) []string {
	startNodes := make([]string, 0)
	for _, id := range topoOrder {
		if d.Nodes[id].InDegree == 0 && info[id].IsCritical {
			startNodes = append(startNodes, id)
		}
	}

	var longestPath []string
	var longestDuration time.Duration

	for _, startID := range startNodes {
		path := make([]string, 0)
		visited := make(map[string]bool)
		d.dfsCriticalPath(startID, info, path, visited, &longestPath, &longestDuration)
	}

	return longestPath
}

func (d *DAG) dfsCriticalPath(
	nodeID string,
	info map[string]*TaskScheduleInfo,
	currentPath []string,
	visited map[string]bool,
	longestPath *[]string,
	longestDuration *time.Duration,
) {
	if visited[nodeID] {
		return
	}
	visited[nodeID] = true
	currentPath = append(currentPath, nodeID)

	node := d.Nodes[nodeID]

	if len(node.OutEdges) == 0 {
		currentDuration := info[nodeID].EarliestFinish
		if currentDuration > *longestDuration ||
			(currentDuration == *longestDuration && len(currentPath) > len(*longestPath)) {
			*longestDuration = currentDuration
			*longestPath = make([]string, len(currentPath))
			copy(*longestPath, currentPath)
		}
	} else {
		hasCriticalNext := false
		for _, nextNode := range node.OutEdges {
			nextID := nextNode.Task.ID
			if info[nextID].IsCritical && !visited[nextID] {
				hasCriticalNext = true
				d.dfsCriticalPath(nextID, info, currentPath, visited, longestPath, longestDuration)
			}
		}
		if !hasCriticalNext {
			currentDuration := info[nodeID].EarliestFinish
			if currentDuration > *longestDuration {
				*longestDuration = currentDuration
				*longestPath = make([]string, len(currentPath))
				copy(*longestPath, currentPath)
			}
		}
	}

	visited[nodeID] = false
}

func (d *DAG) GetMaxParallelism() int {
	topoOrder, err := d.GetTopoOrder()
	if err != nil {
		return 1
	}

	inDegree := make(map[string]int)
	for id, node := range d.Nodes {
		inDegree[id] = node.InDegree
	}

	maxParallel := 0
	processed := make(map[string]bool)
	available := make([]string, 0)

	for _, id := range topoOrder {
		if inDegree[id] == 0 {
			available = append(available, id)
		}
	}

	for len(available) > 0 {
		if len(available) > maxParallel {
			maxParallel = len(available)
		}

		taskID := available[0]
		available = available[1:]
		processed[taskID] = true

		node := d.Nodes[taskID]
		for _, neighbor := range node.OutEdges {
			neighborID := neighbor.Task.ID
			inDegree[neighborID]--
			if inDegree[neighborID] == 0 && !processed[neighborID] {
				available = append(available, neighborID)
			}
		}
	}

	return maxParallel
}

func (c *CriticalPathInfo) Print() {
	fmt.Printf("\n=== Critical Path Analysis ===\n")
	fmt.Printf("Total Estimated Duration: %v\n", c.TotalDuration)
	fmt.Printf("Critical Path (%d tasks):\n", len(c.Path))
	for i, taskID := range c.Path {
		fmt.Printf("  %d. %s\n", i+1, taskID)
	}
	fmt.Println("==============================\n")
}

func PrintScheduleInfo(info map[string]*TaskScheduleInfo) {
	fmt.Println("\n=== Task Schedule Information ===")
	fmt.Printf("%-20s %-12s %-12s %-12s %-12s %-12s %-10s\n",
		"Task ID", "ES", "EF", "LS", "LF", "Slack", "Critical")
	fmt.Println("--------------------------------------------------------------------------------")

	taskIDs := make([]string, 0, len(info))
	for id := range info {
		taskIDs = append(taskIDs, id)
	}
	sort.Strings(taskIDs)

	for _, id := range taskIDs {
		si := info[id]
		critical := "No"
		if si.IsCritical {
			critical = "Yes"
		}
		fmt.Printf("%-20s %-12v %-12v %-12v %-12v %-12v %-10s\n",
			id,
			formatDuration(si.EarliestStart),
			formatDuration(si.EarliestFinish),
			formatDuration(si.LatestStart),
			formatDuration(si.LatestFinish),
			formatDuration(si.Slack),
			critical)
	}
	fmt.Println("================================================================================\n")
}

func formatDuration(d time.Duration) string {
	if d == time.Duration(math.MaxInt64) {
		return "∞"
	}
	return d.Round(time.Second).String()
}
