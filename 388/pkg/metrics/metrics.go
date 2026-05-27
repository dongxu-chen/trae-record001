package metrics

import (
	"net/http"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"

	"container-security-monitor/pkg/detector"
)

type Server struct {
	addr           string
	registry       *prometheus.Registry
	alertCounter   *prometheus.CounterVec
	processEvents  prometheus.Counter
	fileEvents     prometheus.Counter
	networkEvents  prometheus.Counter
	alertEvents    prometheus.Counter
}

func NewServer(addr string) *Server {
	registry := prometheus.NewRegistry()

	alertCounter := prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "csm_security_alerts_total",
			Help: "Total number of security alerts",
		},
		[]string{"rule_name", "severity", "container_id"},
	)

	processEvents := prometheus.NewCounter(prometheus.CounterOpts{
		Name: "csm_process_events_total",
		Help: "Total number of process events monitored",
	})

	fileEvents := prometheus.NewCounter(prometheus.CounterOpts{
		Name: "csm_file_events_total",
		Help: "Total number of file events monitored",
	})

	networkEvents := prometheus.NewCounter(prometheus.CounterOpts{
		Name: "csm_network_events_total",
		Help: "Total number of network events monitored",
	})

	alertEvents := prometheus.NewCounter(prometheus.CounterOpts{
		Name: "csm_alert_events_total",
		Help: "Total number of alert events generated",
	})

	registry.MustRegister(alertCounter)
	registry.MustRegister(processEvents)
	registry.MustRegister(fileEvents)
	registry.MustRegister(networkEvents)
	registry.MustRegister(alertEvents)

	return &Server{
		addr:          addr,
		registry:      registry,
		alertCounter:  alertCounter,
		processEvents: processEvents,
		fileEvents:    fileEvents,
		networkEvents: networkEvents,
		alertEvents:   alertEvents,
	}
}

func (s *Server) Start() error {
	http.Handle("/metrics", promhttp.HandlerFor(s.registry, promhttp.HandlerOpts{}))
	return http.ListenAndServe(s.addr, nil)
}

func (s *Server) RecordAlert(alert *detector.SecurityAlert) {
	s.alertCounter.WithLabelValues(alert.RuleName, alert.Severity, alert.ContainerID).Inc()
	s.alertEvents.Inc()
}

func (s *Server) RecordProcessEvent() {
	s.processEvents.Inc()
}

func (s *Server) RecordFileEvent() {
	s.fileEvents.Inc()
}

func (s *Server) RecordNetworkEvent() {
	s.networkEvents.Inc()
}
