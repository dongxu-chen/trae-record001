package collector

import (
	"log"
	"strings"
	"time"
	"zk-inspector/internal/storage"
	"zk-inspector/internal/types"

	"github.com/go-zookeeper/zk"
)

type ZKCollector struct {
	conn *zk.Conn
}

type traverseItem struct {
	path  string
	depth int
}

func NewZKCollector(servers []string) (*ZKCollector, error) {
	conn, _, err := zk.Connect(servers, 10*time.Second)
	if err != nil {
		return nil, err
	}
	return &ZKCollector{conn: conn}, nil
}

func (c *ZKCollector) Close() {
	c.conn.Close()
}

func (c *ZKCollector) Conn() *zk.Conn {
	return c.conn
}

func (c *ZKCollector) Collect() (*storage.Snapshot, error) {
	snapshot := &storage.Snapshot{
		Timestamp:  time.Now(),
		Nodes:      make(map[string]*types.NodeInfo),
		PathStats:  make(map[string]*storage.PathStat),
		Alerts:     []storage.Alert{},
		TotalNodes: 0,
		TotalSize:  0,
		MaxDepth:   0,
	}

	if err := c.iterativeTraverse(snapshot); err != nil {
		return nil, err
	}

	c.calculatePathStats(snapshot)
	c.generateAlerts(snapshot)

	return snapshot, nil
}

func (c *ZKCollector) iterativeTraverse(snapshot *storage.Snapshot) error {
	stack := []traverseItem{{path: "/", depth: 0}}
	visited := make(map[string]bool)

	for len(stack) > 0 {
		item := stack[len(stack)-1]
		stack = stack[:len(stack)-1]

		if visited[item.path] {
			continue
		}
		visited[item.path] = true

		exists, stat, err := c.conn.Exists(item.path)
		if err != nil {
			log.Printf("Error checking existence of %s: %v", item.path, err)
			continue
		}
		if !exists {
			continue
		}

		children, _, err := c.conn.Children(item.path)
		if err != nil {
			log.Printf("Error getting children of %s: %v", item.path, err)
			continue
		}

		data, _, err := c.conn.Get(item.path)
		if err != nil {
			log.Printf("Error getting data of %s: %v", item.path, err)
			continue
		}

		nodeInfo := &types.NodeInfo{
			Path:         item.path,
			DataSize:     int64(len(data)),
			ChildCount:   len(children),
			Depth:        item.depth,
			Children:     children,
			Ephemeral:    stat.EphemeralOwner != 0,
			LastModified: time.Unix(0, stat.Mtime*int64(time.Millisecond)),
		}

		snapshot.Nodes[item.path] = nodeInfo
		snapshot.TotalNodes++
		snapshot.TotalSize += nodeInfo.DataSize
		if item.depth > snapshot.MaxDepth {
			snapshot.MaxDepth = item.depth
		}

		for i := len(children) - 1; i >= 0; i-- {
			child := children[i]
			childPath := item.path
			if childPath == "/" {
				childPath = "/" + child
			} else {
				childPath = childPath + "/" + child
			}
			if !visited[childPath] {
				stack = append(stack, traverseItem{path: childPath, depth: item.depth + 1})
			}
		}
	}

	return nil
}

func (c *ZKCollector) calculatePathStats(snapshot *storage.Snapshot) {
	for nodePath, node := range snapshot.Nodes {
		parts := strings.Split(strings.Trim(nodePath, "/"), "/")
		for i := 1; i <= len(parts); i++ {
			prefix := "/" + strings.Join(parts[:i], "/")
			if i == 1 && parts[0] == "" {
				prefix = "/"
			}

			if _, exists := snapshot.PathStats[prefix]; !exists {
				snapshot.PathStats[prefix] = &storage.PathStat{
					Path:           prefix,
					NodeCount:      0,
					TotalDataSize:  0,
					MaxDepth:       0,
					AvgDataSize:    0,
					EphemeralCount: 0,
				}
			}

			stat := snapshot.PathStats[prefix]
			stat.NodeCount++
			stat.TotalDataSize += node.DataSize
			if node.Depth > stat.MaxDepth {
				stat.MaxDepth = node.Depth
			}
			if node.Ephemeral {
				stat.EphemeralCount++
			}
		}
	}

	for _, stat := range snapshot.PathStats {
		if stat.NodeCount > 0 {
			stat.AvgDataSize = stat.TotalDataSize / int64(stat.NodeCount)
		}
	}
}

func (c *ZKCollector) generateAlerts(snapshot *storage.Snapshot) {
	thresholdSize := int64(1024 * 1024)
	thresholdChildren := 500
	thresholdDepth := 15

	for nodePath, node := range snapshot.Nodes {
		if node.DataSize > thresholdSize {
			snapshot.Alerts = append(snapshot.Alerts, storage.Alert{
				Type:      "large_data",
				Severity:  "warning",
				Path:      nodePath,
				Message:   "Node data size exceeds threshold",
				Value:     node.DataSize,
				Threshold: thresholdSize,
			})
		}

		if node.ChildCount > thresholdChildren {
			snapshot.Alerts = append(snapshot.Alerts, storage.Alert{
				Type:      "many_children",
				Severity:  "warning",
				Path:      nodePath,
				Message:   "Node has too many children",
				Value:     int64(node.ChildCount),
				Threshold: int64(thresholdChildren),
			})
		}

		if node.Depth > thresholdDepth {
			snapshot.Alerts = append(snapshot.Alerts, storage.Alert{
				Type:      "deep_path",
				Severity:  "info",
				Path:      nodePath,
				Message:   "Node path is too deep",
				Value:     int64(node.Depth),
				Threshold: int64(thresholdDepth),
			})
		}
	}
}

func (c *ZKCollector) StartCollection(storage *storage.MemoryStorage, interval time.Duration) {
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	for range ticker.C {
		snapshot, err := c.Collect()
		if err != nil {
			log.Printf("Collection error: %v", err)
			continue
		}
		storage.AddSnapshot(snapshot)
		log.Printf("Collected snapshot: %d nodes, %d bytes, max depth: %d", snapshot.TotalNodes, snapshot.TotalSize, snapshot.MaxDepth)
	}
}
