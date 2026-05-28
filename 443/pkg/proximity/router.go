package proximity

import (
	"cross-cloud-lb/pkg/model"
	"math"
	"net/http"
	"sync"
	"time"

	"go.uber.org/zap"
)

type ProximityRouter interface {
	GetNearestCluster(clientIP string) (string, float64)
	GetClusterDistance(clusterID string, clientIP string) float64
	CalculateLocationScore(clusterID, clientRegion string) float64
	GetProximityAdjustedWeight(clusterID string, baseWeight int, clientIP string) int
	RegisterCluster(cluster *model.Cluster)
	UpdateRTT(clusterID string, rtt time.Duration)
}

type ProximityRouterImpl struct {
	clusters   map[string]*clusterLocation
	mu         sync.RWMutex
	logger     *zap.Logger
	config     model.ProximityConfig
	geoCache   map[string]string
	rttCache   map[string]time.Duration
}

type clusterLocation struct {
	clusterID string
	provider  model.CloudProvider
	region    string
	latitude  float64
	longitude float64
	avgRTT    time.Duration
	rttCount  int64
}

var regionCoordinates = map[string]struct{ lat, lon float64 }{
	"us-east-1":      {39.0481, -77.4728},
	"us-east-2":      {39.0481, -82.9833},
	"us-west-1":      {37.7749, -122.4194},
	"us-west-2":      {45.5234, -122.6762},
	"eu-west-1":      {53.3478, -6.2597},
	"eu-west-2":      {51.5074, -0.1278},
	"eu-central-1":   {50.1109, 8.6821},
	"ap-northeast-1": {35.6895, 139.6917},
	"ap-southeast-1": {1.3521, 103.8198},
	"ap-southeast-2": {-33.8688, 151.2093},
	"ap-south-1":     {19.0760, 72.8777},
	"eastus":         {37.3719, -79.8164},
	"eastus2":        {36.6681, -78.3889},
	"westus":         {47.6101, -122.3326},
	"westus2":        {47.6101, -122.3326},
	"westeurope":     {52.3676, 4.9041},
	"northeurope":    {53.3478, -6.2597},
	"us-central1":    {41.2619, -95.8608},
	"us-east1":       {33.7208, -84.3879},
	"us-west1":       {45.5946, -122.5200},
	"europe-west1":   {50.8503, 4.3517},
	"asia-east1":     {25.0330, 121.5654},
	"asia-southeast1": {1.3521, 103.8198},
}

var estimatedRegionDistances = map[string]map[string]float64{}

func init() {
	for r1, c1 := range regionCoordinates {
		estimatedRegionDistances[r1] = make(map[string]float64)
		for r2, c2 := range regionCoordinates {
			estimatedRegionDistances[r1][r2] = calculateHaversineDistance(c1.lat, c1.lon, c2.lat, c2.lon)
		}
	}
}

func NewProximityRouter(config model.ProximityConfig, logger *zap.Logger) *ProximityRouterImpl {
	return &ProximityRouterImpl{
		clusters: make(map[string]*clusterLocation),
		logger:   logger,
		config:   config,
		geoCache: make(map[string]string),
		rttCache: make(map[string]time.Duration),
	}
}

func (pr *ProximityRouterImpl) RegisterCluster(cluster *model.Cluster) {
	pr.mu.Lock()
	defer pr.mu.Unlock()

	lat, lon := pr.getRegionCoordinates(cluster.Region)

	pr.clusters[cluster.ID] = &clusterLocation{
		clusterID: cluster.ID,
		provider:  cluster.Provider,
		region:    cluster.Region,
		latitude:  lat,
		longitude: lon,
	}

	pr.logger.Info("Registered cluster for proximity routing",
		zap.String("cluster_id", cluster.ID),
		zap.String("provider", string(cluster.Provider)),
		zap.String("region", cluster.Region),
		zap.Float64("latitude", lat),
		zap.Float64("longitude", lon))
}

func (pr *ProximityRouterImpl) UnregisterCluster(clusterID string) {
	pr.mu.Lock()
	defer pr.mu.Unlock()
	delete(pr.clusters, clusterID)
}

func (pr *ProximityRouterImpl) GetNearestCluster(clientIP string) (string, float64) {
	pr.mu.RLock()
	defer pr.mu.RUnlock()

	if len(pr.clusters) == 0 {
		return "", 0
	}

	clientRegion := pr.getClientRegion(clientIP)

	var nearestCluster string
	minDistance := math.MaxFloat64

	for clusterID, location := range pr.clusters {
		distance := pr.calculateDistance(clientRegion, location.region)
		if location.avgRTT > 0 && pr.config.PreferRTT {
			distance = float64(location.avgRTT.Milliseconds())
		}

		if distance < minDistance {
			minDistance = distance
			nearestCluster = clusterID
		}
	}

	return nearestCluster, minDistance
}

func (pr *ProximityRouterImpl) GetClusterDistance(clusterID string, clientIP string) float64 {
	pr.mu.RLock()
	defer pr.mu.RUnlock()

	location, exists := pr.clusters[clusterID]
	if !exists {
		return math.MaxFloat64
	}

	clientRegion := pr.getClientRegion(clientIP)
	return pr.calculateDistance(clientRegion, location.region)
}

func (pr *ProximityRouterImpl) CalculateLocationScore(clusterID, clientRegion string) float64 {
	pr.mu.RLock()
	defer pr.mu.RUnlock()

	location, exists := pr.clusters[clusterID]
	if !exists {
		return 0
	}

	distance := pr.calculateDistance(clientRegion, location.region)

	maxDistance := 20000.0
	score := 1.0 - (distance / maxDistance)
	if score < 0 {
		score = 0
	}

	if location.avgRTT > 0 && pr.config.PreferRTT {
		rttScore := 1.0 - math.Min(float64(location.avgRTT.Milliseconds())/500.0, 1.0)
		score = score*0.3 + rttScore*0.7
	}

	return score
}

func (pr *ProximityRouterImpl) GetProximityAdjustedWeight(clusterID string, baseWeight int, clientIP string) int {
	if !pr.config.Enabled {
		return baseWeight
	}

	pr.mu.RLock()
	defer pr.mu.RUnlock()

	location, exists := pr.clusters[clusterID]
	if !exists {
		return baseWeight
	}

	clientRegion := pr.getClientRegion(clientIP)

	distances := make([]float64, 0, len(pr.clusters))
	for _, loc := range pr.clusters {
		dist := pr.calculateDistance(clientRegion, loc.region)
		distances = append(distances, dist)
	}

	if len(distances) <= 1 {
		return baseWeight
	}

	minDist := distances[0]
	maxDist := distances[0]
	for _, d := range distances {
		if d < minDist {
			minDist = d
		}
		if d > maxDist {
			maxDist = d
		}
	}

	currentDist := pr.calculateDistance(clientRegion, location.region)

	var proximityFactor float64
	if maxDist == minDist {
		proximityFactor = 1.0
	} else {
		proximityFactor = 1.0 - (currentDist-minDist)/(maxDist-minDist)
	}

	weightInfluence := pr.config.WeightInfluence
	if weightInfluence == 0 {
		weightInfluence = 0.3
	}

	adjustment := 1.0 + (proximityFactor-0.5)*2*weightInfluence
	adjustedWeight := float64(baseWeight) * adjustment

	return int(adjustedWeight + 0.5)
}

func (pr *ProximityRouterImpl) UpdateRTT(clusterID string, rtt time.Duration) {
	pr.mu.Lock()
	defer pr.mu.Unlock()

	location, exists := pr.clusters[clusterID]
	if !exists {
		return
	}

	if location.avgRTT == 0 {
		location.avgRTT = rtt
	} else {
		location.avgRTT = time.Duration((float64(location.avgRTT)*9 + float64(rtt)) / 10)
	}
	location.rttCount++
}

func (pr *ProximityRouterImpl) getRegionCoordinates(region string) (float64, float64) {
	if coords, exists := regionCoordinates[region]; exists {
		return coords.lat, coords.lon
	}
	return 0.0, 0.0
}

func (pr *ProximityRouterImpl) getClientRegion(clientIP string) string {
	pr.mu.RLock()
	if region, exists := pr.geoCache[clientIP]; exists {
		pr.mu.RUnlock()
		return region
	}
	pr.mu.RUnlock()

	region := pr.geoIPLookup(clientIP)

	pr.mu.Lock()
	pr.geoCache[clientIP] = region
	pr.mu.Unlock()

	return region
}

func (pr *ProximityRouterImpl) geoIPLookup(clientIP string) string {
	if clientIP == "" || clientIP == "127.0.0.1" || clientIP == "::1" {
		return "us-east-1"
	}

	return "us-east-1"
}

func (pr *ProximityRouterImpl) calculateDistance(regionA, regionB string) float64 {
	if regionA == regionB {
		return 0
	}

	if distances, exists := estimatedRegionDistances[regionA]; exists {
		if dist, exists := distances[regionB]; exists {
			return dist
		}
	}

	latA, lonA := pr.getRegionCoordinates(regionA)
	latB, lonB := pr.getRegionCoordinates(regionB)

	return calculateHaversineDistance(latA, lonA, latB, lonB)
}

func calculateHaversineDistance(lat1, lon1, lat2, lon2 float64) float64 {
	const earthRadiusKm = 6371.0

	lat1Rad := lat1 * math.Pi / 180
	lat2Rad := lat2 * math.Pi / 180
	deltaLat := (lat2 - lat1) * math.Pi / 180
	deltaLon := (lon2 - lon1) * math.Pi / 180

	a := math.Sin(deltaLat/2)*math.Sin(deltaLat/2) +
		math.Cos(lat1Rad)*math.Cos(lat2Rad)*
			math.Sin(deltaLon/2)*math.Sin(deltaLon/2)
	c := 2 * math.Atan2(math.Sqrt(a), math.Sqrt(1-a))

	return earthRadiusKm * c
}

func (pr *ProximityRouterImpl) GetClientRegionFromRequest(req *http.Request) string {
	clientIP := req.Header.Get("X-Forwarded-For")
	if clientIP == "" {
		clientIP = req.RemoteAddr
	}

	return pr.getClientRegion(clientIP)
}

func (pr *ProximityRouterImpl) GetSortedClustersByProximity(clientIP string) []string {
	pr.mu.RLock()
	defer pr.mu.RUnlock()

	type clusterDistance struct {
		clusterID string
		distance  float64
	}

	distances := make([]clusterDistance, 0, len(pr.clusters))
	clientRegion := pr.getClientRegion(clientIP)

	for clusterID, location := range pr.clusters {
		dist := pr.calculateDistance(clientRegion, location.region)
		distances = append(distances, clusterDistance{clusterID, dist})
	}

	for i := 0; i < len(distances); i++ {
		for j := i + 1; j < len(distances); j++ {
			if distances[i].distance > distances[j].distance {
				distances[i], distances[j] = distances[j], distances[i]
			}
		}
	}

	result := make([]string, len(distances))
	for i, cd := range distances {
		result[i] = cd.clusterID
	}

	return result
}

func (pr *ProximityRouterImpl) GetOptimalOriginCluster(clientIP string, healthyClusters []string) string {
	sorted := pr.GetSortedClustersByProximity(clientIP)

	healthySet := make(map[string]bool)
	for _, c := range healthyClusters {
		healthySet[c] = true
	}

	for _, clusterID := range sorted {
		if healthySet[clusterID] {
			return clusterID
		}
	}

	if len(healthyClusters) > 0 {
		return healthyClusters[0]
	}

	return ""
}
