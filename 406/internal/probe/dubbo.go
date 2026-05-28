package probe

import (
	"context"
	"encoding/binary"
	"net"
	"time"
	"health-check/internal/model"
)

type DubboProber struct{}

func NewDubboProber() *DubboProber {
	return &DubboProber{}
}

const (
	dubboMagic      uint16 = 0xdabb
	dubboRequestFlag byte  = 0xc2
	dubboVersion    byte  = 2
)

type dubboHeader struct {
	Magic    uint16
	Flag     byte
	Status   byte
	ID       uint64
	DataLen  uint32
}

func (p *DubboProber) Probe(ctx context.Context, endpoint *model.Endpoint) *model.ProbeResult {
	result := &model.ProbeResult{
		EndpointID: endpoint.ID,
		Name:       endpoint.Name,
		Protocol:   endpoint.Protocol,
		Timestamp:  time.Now(),
		Status:     model.StatusUp,
	}

	cfg := endpoint.DubboConfig
	if cfg == nil {
		cfg = &model.DubboConfig{
			Interface: "org.apache.dubbo.health.HealthService",
			Method:    "ping",
		}
	}

	start := time.Now()
	conn, err := net.DialTimeout("tcp", endpoint.Address, time.Duration(endpoint.Timeout)*time.Second)
	result.Latency = time.Since(start)

	if err != nil {
		result.Status = model.StatusDown
		result.Error = "connection failed: " + err.Error()
		return result
	}
	defer conn.Close()

	deadline := time.Now().Add(time.Duration(endpoint.Timeout) * time.Second)
	conn.SetDeadline(deadline)

	if cfg.Interface == "" || cfg.Method == "" {
		result.Status = model.StatusUp
		return result
	}

	request := buildDubboRequest(cfg)
	start = time.Now()
	_, err = conn.Write(request)
	if err != nil {
		result.Status = model.StatusDown
		result.Error = "send request failed: " + err.Error()
		return result
	}

	respHeader := make([]byte, 16)
	_, err = conn.Read(respHeader)
	writeLatency := time.Since(start)
	result.Latency += writeLatency

	if err != nil {
		result.Status = model.StatusDown
		result.Error = "read response failed: " + err.Error()
		return result
	}

	magic := binary.BigEndian.Uint16(respHeader[0:2])
	if magic != dubboMagic {
		result.Status = model.StatusDown
		result.Error = "invalid dubbo magic"
		return result
	}

	status := respHeader[3]
	if status != 20 {
		result.Status = model.StatusDown
		result.Error = "dubbo status error: " + string(status)
		return result
	}

	if result.Latency > time.Duration(endpoint.Timeout)*time.Second/2 {
		result.Status = model.StatusDegrade
	}

	return result
}

func buildDubboRequest(cfg *model.DubboConfig) []byte {
	body := make([]byte, 0)

	body = append(body, dubboVersion)

	path := []byte(cfg.Interface)
	pathLen := byte(len(path))
	body = append(body, pathLen)
	body = append(body, path...)

	version := []byte(cfg.Version)
	verLen := byte(len(version))
	body = append(body, verLen)
	body = append(body, version...)

	method := []byte(cfg.Method)
	methodLen := byte(len(method))
	body = append(body, methodLen)
	body = append(body, method...)

	desc := []byte("()")
	descLen := byte(len(desc))
	body = append(body, descLen)
	body = append(body, desc...)

	if cfg.Group != "" {
		group := []byte(cfg.Group)
		groupLen := byte(len(group))
		body = append(body, groupLen)
		body = append(body, group...)
	}

	header := make([]byte, 16)
	binary.BigEndian.PutUint16(header[0:2], dubboMagic)
	header[2] = dubboRequestFlag
	header[3] = 0
	binary.BigEndian.PutUint64(header[4:12], uint64(time.Now().UnixNano()))
	binary.BigEndian.PutUint32(header[12:16], uint32(len(body)))

	return append(header, body...)
}
