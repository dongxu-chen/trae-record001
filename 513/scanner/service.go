package scanner

import (
	"bufio"
	"fmt"
	"net"
	"regexp"
	"strings"
	"time"
)

var globalSignatureManager *SignatureManager

func init() {
	globalSignatureManager = NewSignatureManager()
	globalSignatureManager.Load()
}

func GetSignatureManager() *SignatureManager {
	return globalSignatureManager
}

func DetectService(target string, port int, timeout time.Duration) ServiceFingerprint {
	return DetectServiceWithSignature(target, port, timeout, globalSignatureManager)
}

func extractVersionFromResponse(response string, patterns []VersionPattern) string {
	for _, vp := range patterns {
		if strings.Contains(response, vp.Pattern) {
			re := regexp.MustCompile(vp.Regex)
			matches := re.FindStringSubmatch(response)
			if len(matches) > 1 {
				return matches[1]
			}
		}
	}
	return "unknown"
}

func DetectServiceWithSignature(target string, port int, timeout time.Duration, sm *SignatureManager) ServiceFingerprint {
	fingerprint := ServiceFingerprint{
		Port:     port,
		Service:  "unknown",
		Version:  "unknown",
		Protocol: "TCP",
	}

	sig, hasSig := sm.GetSignature(port)
	if hasSig {
		fingerprint.Service = sig.Service
	}

	address := fmt.Sprintf("%s:%d", target, port)
	conn, err := net.DialTimeout("tcp", address, timeout)
	if err != nil {
		return fingerprint
	}
	defer conn.Close()

	conn.SetReadDeadline(time.Now().Add(timeout))

	if hasSig && len(sig.Probes) > 0 {
		for _, probe := range sig.Probes {
			if probe.Payload != "" {
				conn.Write([]byte(probe.Payload))
			}

			buf := make([]byte, 4096)
			n, err := conn.Read(buf)
			if err == nil && n > 0 {
				response := string(buf[:n])

				if strings.Contains(response, probe.Expected) {
					fingerprint.Version = extractVersionFromResponse(response, sig.VersionPatterns)
					if fingerprint.Version != "unknown" {
						break
					}
				}
			}
		}
	} else {
		switch port {
		case 21:
			fingerprint = detectFTP(conn)
		case 22:
			fingerprint = detectSSH(conn)
		case 80, 8080:
			fingerprint = detectHTTP(conn, address)
		case 6379:
			fingerprint = detectRedis(conn, timeout)
		case 3306:
			fingerprint = detectMySQL(conn, timeout)
		default:
			reader := bufio.NewReader(conn)
			banner, err := reader.ReadString('\n')
			if err == nil && len(banner) > 0 {
				fingerprint.Version = strings.TrimSpace(banner)
			}
		}
	}

	return fingerprint
}

func detectFTP(conn net.Conn) ServiceFingerprint {
	reader := bufio.NewReader(conn)
	banner, err := reader.ReadString('\n')
	if err != nil {
		return ServiceFingerprint{Port: 21, Service: "FTP", Version: "unknown", Protocol: "TCP"}
	}
	return ServiceFingerprint{Port: 21, Service: "FTP", Version: strings.TrimSpace(banner), Protocol: "TCP"}
}

func detectSSH(conn net.Conn) ServiceFingerprint {
	reader := bufio.NewReader(conn)
	banner, err := reader.ReadString('\n')
	if err != nil {
		return ServiceFingerprint{Port: 22, Service: "SSH", Version: "unknown", Protocol: "TCP"}
	}
	return ServiceFingerprint{Port: 22, Service: "SSH", Version: strings.TrimSpace(banner), Protocol: "TCP"}
}

func detectHTTP(conn net.Conn, address string) ServiceFingerprint {
	port := 80
	if strings.Contains(address, ":8080") {
		port = 8080
	}

	fmt.Fprintf(conn, "GET / HTTP/1.0\r\n\r\n")
	reader := bufio.NewReader(conn)
	status, err := reader.ReadString('\n')
	if err != nil {
		return ServiceFingerprint{Port: port, Service: "HTTP", Version: "unknown", Protocol: "TCP"}
	}

	version := strings.TrimSpace(status)
	for {
		line, err := reader.ReadString('\n')
		if err != nil || line == "\r\n" {
			break
		}
		if strings.HasPrefix(strings.ToLower(line), "server:") {
			version = strings.TrimSpace(strings.TrimPrefix(line, "Server:"))
			break
		}
	}

	return ServiceFingerprint{Port: port, Service: "HTTP", Version: version, Protocol: "TCP"}
}

func detectRedis(conn net.Conn, timeout time.Duration) ServiceFingerprint {
	conn.SetReadDeadline(time.Now().Add(timeout))
	fmt.Fprintf(conn, "INFO\r\n")
	reader := bufio.NewReader(conn)
	response, err := reader.ReadString('\n')
	if err != nil {
		return ServiceFingerprint{Port: 6379, Service: "Redis", Version: "unknown", Protocol: "TCP"}
	}

	version := "unknown"
	if strings.Contains(response, "redis_version") {
		for {
			line, err := reader.ReadString('\n')
			if err != nil {
				break
			}
			if strings.HasPrefix(line, "redis_version:") {
				version = strings.TrimSpace(strings.TrimPrefix(line, "redis_version:"))
				break
			}
		}
	}

	return ServiceFingerprint{Port: 6379, Service: "Redis", Version: version, Protocol: "TCP"}
}

func detectMySQL(conn net.Conn, timeout time.Duration) ServiceFingerprint {
	reader := bufio.NewReader(conn)
	header := make([]byte, 4)
	_, err := conn.Read(header)
	if err != nil {
		return ServiceFingerprint{Port: 3306, Service: "MySQL", Version: "unknown", Protocol: "TCP"}
	}

	version := "unknown"
	data := make([]byte, 256)
	n, err := reader.Read(data)
	if err == nil && n > 0 {
		if data[0] == 0x0a {
			end := 0
			for i := 1; i < n; i++ {
				if data[i] == 0x00 {
					end = i
					break
				}
			}
			if end > 1 {
				version = string(data[1:end])
			}
		}
	}

	return ServiceFingerprint{Port: 3306, Service: "MySQL", Version: version, Protocol: "TCP"}
}

func (sc *ScanConfig) ScanWithServiceDetection() []PortResult {
	return sc.ScanWithServiceDetectionManager(globalSignatureManager)
}

func (sc *ScanConfig) ScanWithServiceDetectionManager(sm *SignatureManager) []PortResult {
	openPorts := sc.Scan()
	results := make([]PortResult, 0, len(openPorts))

	for _, port := range openPorts {
		fingerprint := DetectServiceWithSignature(sc.Target, port.Port, sc.Timeout, sm)
		port.Service = fingerprint.Service
		port.Version = fingerprint.Version
		results = append(results, port)
	}

	return results
}
