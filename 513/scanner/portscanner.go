package scanner

import (
	"fmt"
	"net"
	"sync"
	"time"
)

type PortResult struct {
	Port     int
	State    string
	Service  string
	Version  string
	RiskLevel string
}

type ScanConfig struct {
	Target    string
	StartPort int
	EndPort   int
	Timeout   time.Duration
	Threads   int
}

func NewScanConfig(target string, startPort, endPort int, timeout time.Duration, threads int) *ScanConfig {
	return &ScanConfig{
		Target:    target,
		StartPort: startPort,
		EndPort:   endPort,
		Timeout:   timeout,
		Threads:   threads,
	}
}

func (sc *ScanConfig) ScanPort(port int) (PortResult, error) {
	result := PortResult{Port: port, State: "closed"}
	address := fmt.Sprintf("%s:%d", sc.Target, port)
	
	conn, err := net.DialTimeout("tcp", address, sc.Timeout)
	if err != nil {
		return result, err
	}
	defer conn.Close()
	
	result.State = "open"
	return result, nil
}

func (sc *ScanConfig) Scan() []PortResult {
	var results []PortResult
	var wg sync.WaitGroup
	var mutex sync.Mutex
	
	semaphore := make(chan struct{}, sc.Threads)
	ports := make([]int, 0, sc.EndPort - sc.StartPort + 1)
	
	for port := sc.StartPort; port <= sc.EndPort; port++ {
		ports = append(ports, port)
	}
	
	for _, port := range ports {
		wg.Add(1)
		semaphore <- struct{}{}
		
		go func(p int) {
			defer wg.Done()
			defer func() { <-semaphore }()
			
			result, _ := sc.ScanPort(p)
			if result.State == "open" {
				mutex.Lock()
				results = append(results, result)
				mutex.Unlock()
			}
		}(port)
	}
	
	wg.Wait()
	
	return results
}
