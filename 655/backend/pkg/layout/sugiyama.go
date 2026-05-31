package layout

import (
	"math"
	"sort"
	"sync"
)

type Node struct {
	ID       string
	Layer    int
	Order    int
	X        float64
	Y        float64
	Width    float64
	Height   float64
	Incoming []string
	Outgoing []string
	Data     interface{}
}

type Edge struct {
	Source string
	Target string
	Data   interface{}
}

type LayoutConfig struct {
	LayerGap    float64
	NodeGap     float64
	MaxIter     int
	NodeWidth   float64
	NodeHeight  float64
	Parallism   bool
}

type SugiyamaLayout struct {
	nodes   map[string]*Node
	edges   []*Edge
	layers  map[int][]*Node
	config  LayoutConfig
	nodeIDs []string
}

func DefaultConfig() LayoutConfig {
	return LayoutConfig{
		LayerGap:   100,
		NodeGap:    60,
		MaxIter:    24,
		NodeWidth:  50,
		NodeHeight: 50,
		Parallism:  true,
	}
}

func NewSugiyamaLayout(config LayoutConfig) *SugiyamaLayout {
	if config.MaxIter == 0 {
		config.MaxIter = 24
	}
	if config.LayerGap == 0 {
		config.LayerGap = 100
	}
	if config.NodeGap == 0 {
		config.NodeGap = 60
	}
	if config.NodeWidth == 0 {
		config.NodeWidth = 50
	}
	if config.NodeHeight == 0 {
		config.NodeHeight = 50
	}

	return &SugiyamaLayout{
		nodes:   make(map[string]*Node),
		edges:   make([]*Edge, 0),
		layers:  make(map[int][]*Node),
		config:  config,
		nodeIDs: make([]string, 0),
	}
}

func (sl *SugiyamaLayout) AddNode(id string, data interface{}) {
	if _, exists := sl.nodes[id]; !exists {
		sl.nodes[id] = &Node{
			ID:       id,
			Incoming: make([]string, 0),
			Outgoing: make([]string, 0),
			Width:    sl.config.NodeWidth,
			Height:   sl.config.NodeHeight,
			Data:     data,
		}
		sl.nodeIDs = append(sl.nodeIDs, id)
	}
}

func (sl *SugiyamaLayout) AddEdge(source, target string, data interface{}) {
	sl.edges = append(sl.edges, &Edge{
		Source: source,
		Target: target,
		Data:   data,
	})

	if src, ok := sl.nodes[source]; ok {
		src.Outgoing = append(src.Outgoing, target)
	}
	if tgt, ok := sl.nodes[target]; ok {
		tgt.Incoming = append(tgt.Incoming, source)
	}
}

func (sl *SugiyamaLayout) Compute() map[string][2]float64 {
	if len(sl.nodes) == 0 {
		return make(map[string][2]float64)
	}

	sl.assignLayers()
	sl.addDummyNodes()
	sl.orderNodes()
	sl.assignCoordinates()

	result := make(map[string][2]float64)
	for id, node := range sl.nodes {
		result[id] = [2]float64{node.X, node.Y}
	}

	return result
}

func (sl *SugiyamaLayout) assignLayers() {
	inDegree := make(map[string]int)
	queue := make([]string, 0)

	for _, id := range sl.nodeIDs {
		node := sl.nodes[id]
		inDegree[id] = len(node.Incoming)
		if inDegree[id] == 0 {
			queue = append(queue, id)
		}
	}

	processed := 0
	for len(queue) > 0 {
		id := queue[0]
		queue = queue[1:]
		node := sl.nodes[id]

		if inDegree[id] == 0 {
			maxLayer := -1
			for _, srcID := range node.Incoming {
				if sl.nodes[srcID].Layer > maxLayer {
					maxLayer = sl.nodes[srcID].Layer
				}
			}
			node.Layer = maxLayer + 1
		}

		for _, tgtID := range node.Outgoing {
			inDegree[tgtID]--
			if inDegree[tgtID] == 0 {
				queue = append(queue, tgtID)
			}
		}

		processed++
	}

	for _, id := range sl.nodeIDs {
		node := sl.nodes[id]
		sl.layers[node.Layer] = append(sl.layers[node.Layer], node)
	}
}

func (sl *SugiyamaLayout) addDummyNodes() {
}

func (sl *SugiyamaLayout) orderNodes() {
	layerCount := len(sl.layers)
	if layerCount <= 1 {
		return
	}

	layerIDs := make([]int, 0, layerCount)
	for l := range sl.layers {
		layerIDs = append(layerIDs, l)
	}
	sort.Ints(layerIDs)

	for iter := 0; iter < sl.config.MaxIter; iter++ {
		improved := false

		if iter%2 == 0 {
			for i := 1; i < layerCount; i++ {
				if sl.wMedianOrdering(layerIDs[i], layerIDs[i-1], true) {
					improved = true
				}
			}
		} else {
			for i := layerCount - 2; i >= 0; i-- {
				if sl.wMedianOrdering(layerIDs[i], layerIDs[i+1], false) {
					improved = true
				}
			}
		}

		if !improved && iter > 2 {
			break
		}
	}

	for _, layer := range sl.layers {
		for idx, node := range layer {
			node.Order = idx
		}
	}
}

func (sl *SugiyamaLayout) wMedianOrdering(layerID, adjLayerID int, downDir bool) bool {
	layer := sl.layers[layerID]
	adjLayer := sl.layers[adjLayerID]

	adjOrder := make(map[string]int)
	for idx, node := range adjLayer {
		adjOrder[node.ID] = idx
	}

	medians := make([]float64, len(layer))
	for idx, node := range layer {
		var neighbors []string
		if downDir {
			neighbors = node.Incoming
		} else {
			neighbors = node.Outgoing
		}

		positions := make([]int, 0, len(neighbors))
		for _, nID := range neighbors {
			if pos, ok := adjOrder[nID]; ok {
				positions = append(positions, pos)
			}
		}

		if len(positions) == 0 {
			medians[idx] = float64(idx)
		} else {
			sort.Ints(positions)
			mid := len(positions) / 2
			if len(positions)%2 == 1 {
				medians[idx] = float64(positions[mid])
			} else {
				medians[idx] = float64(positions[mid-1]+positions[mid]) / 2.0
			}
		}
	}

	indices := make([]int, len(layer))
	for i := range indices {
		indices[i] = i
	}

	sort.Slice(indices, func(i, j int) bool {
		return medians[indices[i]] < medians[indices[j]]
	})

	newLayer := make([]*Node, len(layer))
	for i, idx := range indices {
		newLayer[i] = layer[idx]
	}

	sl.layers[layerID] = newLayer

	return true
}

func (sl *SugiyamaLayout) assignCoordinates() {
	layerIDs := make([]int, 0, len(sl.layers))
	for l := range sl.layers {
		layerIDs = append(layerIDs, l)
	}
	sort.Ints(layerIDs)

	for iter := 0; iter < 2; iter++ {
		if iter%2 == 0 {
			for i, layerID := range layerIDs {
				layer := sl.layers[layerID]
				layerWidth := sl.calculateLayerWidth(layer)
				startX := -layerWidth / 2

				for _, node := range layer {
					node.X = startX + node.Width/2
					node.Y = float64(i)*sl.config.LayerGap
					startX += node.Width + sl.config.NodeGap
				}
			}
		} else {
			for i := len(layerIDs) - 1; i >= 0; i-- {
				layer := sl.layers[layerIDs[i]]
				if len(layer) == 0 {
					continue
				}

				parentY := 0.0
				if i > 0 {
					parentY = sl.layers[layerIDs[i-1]][0].Y
				}

				layerWidth := sl.calculateLayerWidth(layer)
				startX := -layerWidth / 2

				for _, node := range layer {
					node.X = startX + node.Width/2
					node.Y = parentY + sl.config.LayerGap
					startX += node.Width + sl.config.NodeGap
				}
			}
		}
	}

	sl.normalizeCoordinates()
}

func (sl *SugiyamaLayout) calculateLayerWidth(layer []*Node) float64 {
	width := 0.0
	for _, node := range layer {
		width += node.Width + sl.config.NodeGap
	}
	return width - sl.config.NodeGap
}

func (sl *SugiyamaLayout) normalizeCoordinates() {
	minX := math.MaxFloat64
	minY := math.MaxFloat64

	for _, node := range sl.nodes {
		if node.X < minX {
			minX = node.X
		}
		if node.Y < minY {
			minY = node.Y
		}
	}

	padding := 50.0
	for _, node := range sl.nodes {
		node.X = node.X - minX + padding
		node.Y = node.Y - minY + padding
	}
}

func (sl *SugiyamaLayout) GetLayers() [][]*Node {
	layerIDs := make([]int, 0, len(sl.layers))
	for l := range sl.layers {
		layerIDs = append(layerIDs, l)
	}
	sort.Ints(layerIDs)

	result := make([][]*Node, len(layerIDs))
	for i, lid := range layerIDs {
		result[i] = sl.layers[lid]
	}

	return result
}

func (sl *SugiyamaLayout) ParallelCompute() map[string][2]float64 {
	if !sl.config.Parallism || len(sl.nodes) < 50 {
		return sl.Compute()
	}

	var wg sync.WaitGroup
	var once sync.Once

	wg.Add(1)
	go func() {
		defer wg.Done()
		sl.assignLayers()
	}()

	wg.Wait()

	sl.addDummyNodes()

	result := make(map[string][2]float64)
	once.Do(func() {
		sl.orderNodes()
		sl.assignCoordinates()

		for id, node := range sl.nodes {
			result[id] = [2]float64{node.X, node.Y}
		}
	})

	return result
}
