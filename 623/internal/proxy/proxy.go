package proxy

import (
	"db-guardian/internal/config"
	"db-guardian/internal/leak"
	"db-guardian/internal/lifecycle"
	"db-guardian/internal/limiter"
	"db-guardian/internal/pool"
	"db-guardian/internal/prewarm"
	"db-guardian/pkg/logger"
	"fmt"
	"io"
	"net"
	"sync"
	"sync/atomic"
	"time"
)

type MySQLProxy struct {
	cfg              config.ProxyConfig
	analyzer         *ConnectionAnalyzer
	connLimiter      *limiter.ConnectionLimiter
	clientLimiter    *limiter.ClientRateLimiter
	clientIDLimiter  *limiter.ClientIDLimiter
	leakDetector     *leak.LeakDetector
	scalingPool      *pool.AutoScalingPool
	preWarmEngine    *prewarm.PreWarmEngine
	lifecycleTracker *lifecycle.ConnectionLifecycle
	log              *logger.Logger
	listener         net.Listener
	activeConns      int64
	totalConns       int64
	connections      map[uint64]*TrackedConnection
	connMutex        sync.RWMutex
	connIDCounter    uint64
	shutdownChan     chan struct{}
	wg               sync.WaitGroup
}

type TrackedConnection struct {
	ID         uint64
	ClientIP   string
	ClientID   string
	AppName    string
	ProcessID  string
	Username   string
	ClientConn net.Conn
	ServerConn net.Conn
	StartTime  time.Time
	LastActive time.Time
	QueryCount int64
	isClosed   bool
	mu         sync.Mutex
}

func NewMySQLProxy(cfg config.ProxyConfig, analyzer *ConnectionAnalyzer,
	connLimiter *limiter.ConnectionLimiter, clientLimiter *limiter.ClientRateLimiter,
	clientIDLimiter *limiter.ClientIDLimiter, leakDetector *leak.LeakDetector,
	scalingPool *pool.AutoScalingPool, preWarmEngine *prewarm.PreWarmEngine,
	lifecycleTracker *lifecycle.ConnectionLifecycle,
	log *logger.Logger) *MySQLProxy {
	return &MySQLProxy{
		cfg:              cfg,
		analyzer:         analyzer,
		connLimiter:      connLimiter,
		clientLimiter:    clientLimiter,
		clientIDLimiter:  clientIDLimiter,
		leakDetector:     leakDetector,
		scalingPool:      scalingPool,
		preWarmEngine:    preWarmEngine,
		lifecycleTracker: lifecycleTracker,
		log:              log,
		connections:      make(map[uint64]*TrackedConnection),
		shutdownChan:     make(chan struct{}),
	}
}

func (p *MySQLProxy) Start() error {
	addr := fmt.Sprintf("%s:%d", p.cfg.Host, p.cfg.Port)
	listener, err := net.Listen("tcp", addr)
	if err != nil {
		return fmt.Errorf("failed to start proxy: %w", err)
	}
	p.listener = listener

	p.wg.Add(1)
	go p.cleanupIdleConnections()

	p.log.Info("Proxy started on %s", addr)

	for {
		select {
		case <-p.shutdownChan:
			return nil
		default:
		}

		clientConn, err := listener.Accept()
		if err != nil {
			select {
			case <-p.shutdownChan:
				return nil
			default:
				p.log.Error("Accept error: %v", err)
				continue
			}
		}

		p.wg.Add(1)
		go p.handleConnection(clientConn)
	}
}

func (p *MySQLProxy) handleConnection(clientConn net.Conn) {
	defer p.wg.Done()
	defer clientConn.Close()

	startTime := time.Now()
	clientIP, _, _ := net.SplitHostPort(clientConn.RemoteAddr().String())

	clientID := p.extractClientID(clientConn)
	appName := "unknown"
	processID := "unknown"
	username := "unknown"

	ident := &limiter.ClientIdentifier{
		ClientID:  clientID,
		ClientIP:  clientIP,
		AppName:   appName,
		ProcessID: processID,
		Username:  username,
	}

	connID := atomic.AddUint64(&p.connIDCounter, 1)

	p.lifecycleTracker.RecordEvent(connID, clientID, clientIP, lifecycle.PhaseCreated, "Connection accepted")

	if !p.clientIDLimiter.AllowConnection(clientID, ident) {
		p.log.Warn("Client ID rate limit exceeded: client=%s, ip=%s", clientID, clientIP)
		p.lifecycleTracker.RecordEvent(connID, clientID, clientIP, lifecycle.PhaseRateLimited, "Client ID rate limit exceeded")
		return
	}

	defer p.clientIDLimiter.ReleaseConnection(clientID)

	if !p.clientLimiter.Allow(clientIP) {
		p.log.Warn("Rate limit exceeded for client: %s", clientIP)
		p.lifecycleTracker.RecordEvent(connID, clientID, clientIP, lifecycle.PhaseRateLimited, "IP rate limit exceeded")
		return
	}

	if !p.connLimiter.AllowConnection(clientIP) {
		p.log.Warn("Connection limit exceeded for client: %s", clientIP)
		p.lifecycleTracker.RecordEvent(connID, clientID, clientIP, lifecycle.PhaseRateLimited, "Connection limit exceeded")
		return
	}

	defer p.connLimiter.ReleaseConnection(clientIP)

	p.lifecycleTracker.RecordEvent(connID, clientID, clientIP, lifecycle.PhaseAuthenticating, "Checking warm pool")

	var serverConn net.Conn
	var warmID uint64
	var usedWarmPool bool

	if p.scalingPool != nil {
		if warmConn, wid, ok := p.scalingPool.LeaseWarmConnection(); ok {
			serverConn = warmConn
			warmID = wid
			usedWarmPool = true
			p.lifecycleTracker.RecordEvent(connID, clientID, clientIP, lifecycle.PhasePreWarmed, "Leased from warm pool")
			if p.preWarmEngine != nil {
				p.preWarmEngine.RecordHit()
			}
		}
	}

	if !usedWarmPool {
		if p.preWarmEngine != nil {
			p.preWarmEngine.RecordMiss()
		}

		connectStart := time.Now()
		var err error
		serverConn, err = p.connectToBackend(connectStart, clientIP)
		if err != nil {
			p.log.Error("Failed to connect to backend: %v", err)
			p.lifecycleTracker.RecordTimedEvent(connID, clientID, clientIP, lifecycle.PhaseClosed,
				time.Since(connectStart), fmt.Sprintf("Backend connection failed: %v", err))
			return
		}
		connectDuration := time.Since(connectStart)
		p.lifecycleTracker.RecordTimedEvent(connID, clientID, clientIP, lifecycle.PhaseAuthenticating,
			connectDuration, fmt.Sprintf("Connected to backend in %v", connectDuration))
	}

	defer serverConn.Close()

	tracked := &TrackedConnection{
		ID:         connID,
		ClientIP:   clientIP,
		ClientID:   clientID,
		AppName:    appName,
		ProcessID:  processID,
		Username:   username,
		ClientConn: clientConn,
		ServerConn: serverConn,
		StartTime:  startTime,
		LastActive: time.Now(),
	}

	p.addConnection(tracked)
	defer p.removeConnection(connID)

	if p.leakDetector != nil {
		p.leakDetector.TrackConnection(connID, clientID, clientIP, appName, processID, "")
		defer p.leakDetector.CloseConnection(connID)
	}

	if p.scalingPool != nil {
		p.scalingPool.IncrementActive()
		defer p.scalingPool.DecrementActive()
	}

	atomic.AddInt64(&p.activeConns, 1)
	atomic.AddInt64(&p.totalConns, 1)
	defer atomic.AddInt64(&p.activeConns, -1)

	p.analyzer.RecordConnection(clientIP, startTime, time.Now())

	p.lifecycleTracker.RecordEvent(connID, clientID, clientIP, lifecycle.PhaseActive,
		fmt.Sprintf("Connection active, warm_pool=%v", usedWarmPool))

	p.log.Debug("New connection: id=%d, client=%s, client_id=%s, warm=%v", connID, clientIP, clientID, usedWarmPool)

	var wg sync.WaitGroup
	wg.Add(2)

	go func() {
		defer wg.Done()
		p.copyData(tracked, clientConn, serverConn, "client->server")
	}()

	go func() {
		defer wg.Done()
		p.copyData(tracked, serverConn, clientConn, "server->client")
	}()

	wg.Wait()

	p.lifecycleTracker.RecordEvent(connID, clientID, clientIP, lifecycle.PhaseReleasing, "Connection closing")

	if usedWarmPool && p.scalingPool != nil {
		p.scalingPool.RemoveWarmConnection(warmID)
		p.lifecycleTracker.RecordEvent(connID, clientID, clientIP, lifecycle.PhaseReturned, "Warm connection removed from pool")
	}

	p.lifecycleTracker.RecordEvent(connID, clientID, clientIP, lifecycle.PhaseClosed,
		fmt.Sprintf("Duration=%v, Queries=%d", time.Since(startTime), tracked.QueryCount))
}

func (p *MySQLProxy) extractClientID(conn net.Conn) string {
	addr := conn.RemoteAddr().String()
	return fmt.Sprintf("client_%s", addr)
}

func (p *MySQLProxy) connectToBackend(startTime time.Time, clientIP string) (net.Conn, error) {
	backendAddr := fmt.Sprintf("%s:%d", p.cfg.TargetDBHost, p.cfg.TargetDBPort)
	serverConn, err := net.DialTimeout("tcp", backendAddr, 10*time.Second)
	if err != nil {
		return nil, err
	}

	connectDuration := time.Since(startTime)
	p.analyzer.CheckSlowConnection(clientIP, connectDuration)

	return serverConn, nil
}

func (p *MySQLProxy) copyData(tracked *TrackedConnection, dst, src net.Conn, direction string) {
	buf := make([]byte, 32*1024)
	for {
		select {
		case <-p.shutdownChan:
			return
		default:
		}

		n, err := src.Read(buf)
		if n > 0 {
			tracked.mu.Lock()
			tracked.LastActive = time.Now()
			tracked.QueryCount++
			tracked.mu.Unlock()

			if tracked.QueryCount%100 == 1 && p.lifecycleTracker != nil {
				p.lifecycleTracker.RecordEvent(tracked.ID, tracked.ClientID, tracked.ClientIP,
					lifecycle.PhaseQuerying, fmt.Sprintf("Query #%d", tracked.QueryCount))
			}

			if p.leakDetector != nil {
				p.leakDetector.UpdateConnectionActivity(tracked.ID)
			}

			_, err := dst.Write(buf[:n])
			if err != nil {
				return
			}
		}
		if err != nil {
			if err != io.EOF {
				p.log.Debug("Copy error (%s): %v", direction, err)
			}
			return
		}
	}
}

func (p *MySQLProxy) addConnection(conn *TrackedConnection) {
	p.connMutex.Lock()
	defer p.connMutex.Unlock()
	p.connections[conn.ID] = conn
}

func (p *MySQLProxy) removeConnection(id uint64) {
	p.connMutex.Lock()
	defer p.connMutex.Unlock()
	delete(p.connections, id)
}

func (p *MySQLProxy) cleanupIdleConnections() {
	defer p.wg.Done()
	ticker := time.NewTicker(time.Minute)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			p.checkIdleConnections()
		case <-p.shutdownChan:
			return
		}
	}
}

func (p *MySQLProxy) checkIdleConnections() {
	p.connMutex.RLock()
	defer p.connMutex.RUnlock()

	now := time.Now()
	idleCount := 0

	for _, conn := range p.connections {
		conn.mu.Lock()
		if !conn.isClosed && now.Sub(conn.LastActive) > p.analyzer.cfg.IdleConnectionTimeout {
			p.log.Info("Closing idle connection: id=%d, idle=%v", conn.ID, now.Sub(conn.LastActive))
			conn.isClosed = true
			conn.ClientConn.Close()
			conn.ServerConn.Close()
			idleCount++
		}
		conn.mu.Unlock()
	}

	if idleCount > 0 {
		p.log.Info("Closed %d idle connections", idleCount)
	}
}

func (p *MySQLProxy) Stop() {
	close(p.shutdownChan)
	if p.listener != nil {
		p.listener.Close()
	}

	p.connMutex.Lock()
	for _, conn := range p.connections {
		conn.mu.Lock()
		if !conn.isClosed {
			conn.ClientConn.Close()
			conn.ServerConn.Close()
			conn.isClosed = true
		}
		conn.mu.Unlock()
	}
	p.connMutex.Unlock()

	p.wg.Wait()
}

func (p *MySQLProxy) GetStats() map[string]interface{} {
	return map[string]interface{}{
		"active_connections": atomic.LoadInt64(&p.activeConns),
		"total_connections":  atomic.LoadInt64(&p.totalConns),
		"connection_rate":    p.connLimiter.GetConnectionRate(),
	}
}

func (p *MySQLProxy) GetConnections() []*TrackedConnection {
	p.connMutex.RLock()
	defer p.connMutex.RUnlock()

	conns := make([]*TrackedConnection, 0, len(p.connections))
	for _, conn := range p.connections {
		conns = append(conns, conn)
	}
	return conns
}

func (p *MySQLProxy) ReleaseIdleConnections(count int) int {
	p.connMutex.RLock()
	defer p.connMutex.RUnlock()

	released := 0
	now := time.Now()

	for _, conn := range p.connections {
		if released >= count {
			break
		}
		conn.mu.Lock()
		if !conn.isClosed && now.Sub(conn.LastActive) > 30*time.Second {
			conn.isClosed = true
			conn.ClientConn.Close()
			conn.ServerConn.Close()
			released++
		}
		conn.mu.Unlock()
	}

	return released
}
