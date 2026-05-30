package proxy

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httputil"
	"net/url"
	"strings"
	"time"

	"github.com/sirupsen/logrus"

	"github.com/keymgmt/service/sidecar/internal/secrets"
)

type HTTPProxy struct {
	log            *logrus.Logger
	secretManager  *secrets.SecretManager
	targetURL      *url.URL
	proxy          *httputil.ReverseProxy
	listenAddr     string
	injectHeaders  bool
	injectQuery    bool
	server         *http.Server
}

type Config struct {
	TargetURL    string
	ListenAddr   string
	InjectHeaders bool
	InjectQuery   bool
}

func NewHTTPProxy(log *logrus.Logger, secretManager *secrets.SecretManager, cfg Config) (*HTTPProxy, error) {
	target, err := url.Parse(cfg.TargetURL)
	if err != nil {
		return nil, fmt.Errorf("invalid target URL: %w", err)
	}

	listenAddr := cfg.ListenAddr
	if listenAddr == "" {
		listenAddr = ":8080"
	}

	p := &HTTPProxy{
		log:           log,
		secretManager: secretManager,
		targetURL:     target,
		listenAddr:    listenAddr,
		injectHeaders: cfg.InjectHeaders,
		injectQuery:   cfg.InjectQuery,
	}

	proxy := httputil.NewSingleHostReverseProxy(target)
	originalDirector := proxy.Director
	proxy.Director = func(req *http.Request) {
		originalDirector(req)
		p.modifyRequest(req)
	}

	proxy.ModifyResponse = p.modifyResponse
	proxy.ErrorHandler = p.errorHandler

	p.proxy = proxy

	secretManager.OnUpdate(func(s map[string]*secrets.Secret) {
		log.Infof("Secrets updated, proxy will use new values for future requests")
	})

	return p, nil
}

func (p *HTTPProxy) Start(ctx context.Context) error {
	p.log.Infof("Starting HTTP proxy on %s, forwarding to %s", p.listenAddr, p.targetURL)

	mux := http.NewServeMux()
	mux.HandleFunc("/secrets", p.handleSecretsEndpoint)
	mux.HandleFunc("/secrets/", p.handleSecretEndpoint)
	mux.HandleFunc("/healthz", p.handleHealth)
	mux.HandleFunc("/stats", p.handleStats)
	mux.Handle("/", p.proxy)

	p.server = &http.Server{
		Addr:    p.listenAddr,
		Handler: mux,
	}

	go func() {
		<-ctx.Done()
		p.log.Info("Shutting down HTTP proxy")
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		if err := p.server.Shutdown(shutdownCtx); err != nil {
			p.log.Errorf("Proxy shutdown error: %v", err)
		}
	}()

	if err := p.server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		return fmt.Errorf("proxy server error: %w", err)
	}

	return nil
}

func (p *HTTPProxy) modifyRequest(req *http.Request) {
	if p.injectHeaders {
		allSecrets := p.secretManager.GetAllSecrets()
		for name, secret := range allSecrets {
			headerName := fmt.Sprintf("X-Secret-%s", strings.ToUpper(strings.ReplaceAll(name, "_", "-")))
			req.Header.Set(headerName, secret.Value)
		}
	}

	if p.injectQuery {
		q := req.URL.Query()
		allSecrets := p.secretManager.GetAllSecrets()
		for name, secret := range allSecrets {
			paramName := fmt.Sprintf("secret_%s", name)
			q.Set(paramName, secret.Value)
		}
		req.URL.RawQuery = q.Encode()
	}

	req.Header.Set("X-Secret-Proxy", "keymgmt-sidecar")
}

func (p *HTTPProxy) modifyResponse(resp *http.Response) error {
	resp.Header.Set("X-Secret-Proxy-Version", "1.0")

	count, lastUpdate, _ := p.secretManager.Stats()
	resp.Header.Set("X-Secret-Count", fmt.Sprintf("%d", count))
	if !lastUpdate.IsZero() {
		resp.Header.Set("X-Secret-Last-Update", lastUpdate.Format(time.RFC3339))
	}

	return nil
}

func (p *HTTPProxy) errorHandler(w http.ResponseWriter, r *http.Request, err error) {
	p.log.Errorf("Proxy error: %v", err)
	w.WriteHeader(http.StatusBadGateway)
	fmt.Fprintf(w, "Proxy error: %v", err)
}

func (p *HTTPProxy) handleSecretsEndpoint(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	allSecrets := p.secretManager.GetAllSecrets()
	response := make([]map[string]interface{}, 0, len(allSecrets))
	for name, secret := range allSecrets {
		response = append(response, map[string]interface{}{
			"name":  name,
			"value": secret.Value,
		})
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"secrets": response,
		"total":   len(response),
	})
}

func (p *HTTPProxy) handleSecretEndpoint(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	parts := strings.Split(r.URL.Path, "/")
	if len(parts) < 3 {
		http.Error(w, "Invalid path", http.StatusBadRequest)
		return
	}

	secretName := parts[2]
	secret, exists := p.secretManager.GetSecret(secretName)
	if !exists {
		http.Error(w, "Secret not found", http.StatusNotFound)
		return
	}

	accept := r.Header.Get("Accept")
	if strings.Contains(accept, "application/json") {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"name":  secret.Name,
			"value": secret.Value,
		})
	} else {
		w.Header().Set("Content-Type", "text/plain")
		w.Write([]byte(secret.Value))
	}
}

func (p *HTTPProxy) handleHealth(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"status": "healthy",
		"target": p.targetURL.String(),
	})
}

func (p *HTTPProxy) handleStats(w http.ResponseWriter, r *http.Request) {
	count, lastUpdate, updateCount := p.secretManager.Stats()

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"secret_count":     count,
		"last_update":      lastUpdate,
		"total_updates":    updateCount,
		"target":           p.targetURL.String(),
		"inject_headers":   p.injectHeaders,
		"inject_query":     p.injectQuery,
	})
}
