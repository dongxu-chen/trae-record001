package main

import (
	"context"
	"flag"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"github.com/sirupsen/logrus"

	"github.com/keymgmt/service/sidecar/internal/proxy"
	"github.com/keymgmt/service/sidecar/internal/secrets"
)

var (
	targetURL     = flag.String("target", "http://localhost:8081", "Target application URL to proxy")
	listenAddr    = flag.String("listen", ":8080", "Proxy listen address")
	apiURL        = flag.String("api-url", "", "Key Management API URL (optional)")
	apiToken      = flag.String("api-token", "", "API authentication token (optional)")
	watchPaths    = flag.String("watch-paths", "", "Comma-separated paths to watch for secret files")
	pollInterval  = flag.Int("poll-interval", 30, "API polling interval in seconds")
	injectHeaders = flag.Bool("inject-headers", true, "Inject secrets as HTTP headers")
	injectQuery   = flag.Bool("inject-query", false, "Inject secrets as query parameters")
	logLevel      = flag.String("log-level", "info", "Log level (debug, info, warn, error)")
)

func main() {
	flag.Parse()

	log := logrus.New()
	log.SetFormatter(&logrus.JSONFormatter{})
	log.SetOutput(os.Stdout)

	level, err := logrus.ParseLevel(*logLevel)
	if err != nil {
		level = logrus.InfoLevel
	}
	log.SetLevel(level)

	log.Info("Starting Key Management Sidecar Proxy")

	var paths []string
	if *watchPaths != "" {
		paths = strings.Split(*watchPaths, ",")
		for i, p := range paths {
			paths[i] = strings.TrimSpace(p)
		}
		log.Infof("Watching paths: %v", paths)
	}

	secretCfg := secrets.Config{
		APIBaseURL:   *apiURL,
		APIToken:     *apiToken,
		WatchPaths:   paths,
		PollInterval: time.Duration(*pollInterval) * time.Second,
	}

	secretManager := secrets.NewSecretManager(log, secretCfg)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	if err := secretManager.Start(ctx); err != nil {
		log.Fatalf("Failed to start secret manager: %v", err)
	}
	defer secretManager.Stop()

	proxyCfg := proxy.Config{
		TargetURL:    *targetURL,
		ListenAddr:   *listenAddr,
		InjectHeaders: *injectHeaders,
		InjectQuery:  *injectQuery,
	}

	httpProxy, err := proxy.NewHTTPProxy(log, secretManager, proxyCfg)
	if err != nil {
		log.Fatalf("Failed to create HTTP proxy: %v", err)
	}

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		sig := <-sigCh
		log.Infof("Received signal: %v, shutting down", sig)
		cancel()
	}()

	log.Infof("Sidecar proxy started - listening on %s, forwarding to %s", *listenAddr, *targetURL)

	if err := httpProxy.Start(ctx); err != nil {
		log.Fatalf("Proxy error: %v", err)
	}

	log.Info("Sidecar proxy stopped")
}
