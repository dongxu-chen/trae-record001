package main

import (
	"flag"
	"os"
	"time"

	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
	"k8s.io/apimachinery/pkg/runtime"
	utilruntime "k8s.io/apimachinery/pkg/util/runtime"
	clientgoscheme "k8s.io/client-go/kubernetes/scheme"
	_ "k8s.io/client-go/plugin/pkg/client/auth"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/healthz"

	healthv1 "github.com/k8s-health-checker/operator/api/v1"
	"github.com/k8s-health-checker/operator/internal/controller"
	"github.com/k8s-health-checker/operator/internal/metrics"
	"github.com/k8s-health-checker/operator/internal/notifications"
	"github.com/k8s-health-checker/operator/internal/remediation"
)

var (
	scheme   = runtime.NewScheme()
	setupLog = ctrl.Log.WithName("setup")
)

func init() {
	utilruntime.Must(clientgoscheme.AddToScheme(scheme))
	utilruntime.Must(healthv1.AddToScheme(scheme))
}

func main() {
	var (
		metricsAddr          string
		enableLeaderElection bool
		probeAddr            string
		dingtalkWebhook      string
		dingtalkSecret       string
		weworkWebhook        string
		logLevel             string
	)

	flag.StringVar(&metricsAddr, "metrics-bind-address", ":8080", "The address the metric endpoint binds to.")
	flag.StringVar(&probeAddr, "health-probe-bind-address", ":8081", "The address the probe endpoint binds to.")
	flag.BoolVar(&enableLeaderElection, "leader-elect", false,
		"Enable leader election for controller manager. Enabling this will ensure there is only one active controller manager.")
	flag.StringVar(&dingtalkWebhook, "dingtalk-webhook", "", "DingTalk webhook URL for alerts")
	flag.StringVar(&dingtalkSecret, "dingtalk-secret", "", "DingTalk webhook secret")
	flag.StringVar(&weworkWebhook, "wework-webhook", "", "WeCom webhook URL for alerts")
	flag.StringVar(&logLevel, "log-level", "info", "Log level (debug, info, warn, error)")
	flag.Parse()

	// Initialize logger
	logger, err := initLogger(logLevel)
	if err != nil {
		setupLog.Error(err, "unable to initialize logger")
		os.Exit(1)
	}
	defer logger.Sync()

	ctrl.SetLogger(zap.New(logger.Core()))

	// Initialize alert router
	alertRouter := &notifications.AlertRouter{
		Logger: logger,
	}

	if dingtalkWebhook != "" {
		alertRouter.DingTalkConfig = &notifications.DingTalkConfig{
			WebhookURL: dingtalkWebhook,
			Secret:     dingtalkSecret,
		}
	}

	if weworkWebhook != "" {
		alertRouter.WeWorkConfig = &notifications.WeWorkConfig{
			WebhookURL: weworkWebhook,
		}
	}

	// Initialize metrics
	metrics := metrics.NewHealthCheckMetrics()

	// Create manager
	mgr, err := ctrl.NewManager(ctrl.GetConfigOrDie(), ctrl.Options{
		Scheme:                 scheme,
		MetricsBindAddress:     metricsAddr,
		Port:                   9443,
		HealthProbeBindAddress: probeAddr,
		LeaderElection:         enableLeaderElection,
		LeaderElectionID:       "healthcheck-operator-lock",
		LeaseDuration:          &[]time.Duration{15 * time.Second}[0],
		RenewDeadline:          &[]time.Duration{10 * time.Second}[0],
		RetryPeriod:            &[]time.Duration{2 * time.Second}[0],
	})
	if err != nil {
		setupLog.Error(err, "unable to start manager")
		os.Exit(1)
	}

	// Initialize remediator
	remediator := &remediation.Remediator{
		Client: mgr.GetClient(),
		Logger: logger,
	}

	// Setup controller
	if err = (&controller.HealthCheckReconciler{
		Client:     mgr.GetClient(),
		Scheme:     mgr.GetScheme(),
		Logger:     logger,
		Metrics:    metrics,
		Remediator: remediator,
	}).SetupWithManager(mgr); err != nil {
		setupLog.Error(err, "unable to create controller", "controller", "HealthCheck")
		os.Exit(1)
	}

	// Setup health probes
	if err := mgr.AddHealthzCheck("healthz", healthz.Ping); err != nil {
		setupLog.Error(err, "unable to set up health check")
		os.Exit(1)
	}
	if err := mgr.AddReadyzCheck("readyz", healthz.Ping); err != nil {
		setupLog.Error(err, "unable to set up ready check")
		os.Exit(1)
	}

	logger.Info("starting manager")
	if err := mgr.Start(ctrl.SetupSignalHandler()); err != nil {
		setupLog.Error(err, "problem running manager")
		os.Exit(1)
	}
}

func initLogger(level string) (*zap.Logger, error) {
	var lvl zapcore.Level
	if err := lvl.UnmarshalText([]byte(level)); err != nil {
		return nil, err
	}

	config := zap.Config{
		Level:       zap.NewAtomicLevelAt(lvl),
		Development: false,
		Sampling: &zap.SamplingConfig{
			Initial:    100,
			Thereafter: 100,
		},
		Encoding: "json",
		EncoderConfig: zapcore.EncoderConfig{
			TimeKey:        "timestamp",
			LevelKey:       "level",
			NameKey:        "logger",
			CallerKey:      "caller",
			FunctionKey:    zapcore.OmitKey,
			MessageKey:     "message",
			StacktraceKey:  "stacktrace",
			LineEnding:     zapcore.DefaultLineEnding,
			EncodeLevel:    zapcore.LowercaseLevelEncoder,
			EncodeTime:     zapcore.ISO8601TimeEncoder,
			EncodeDuration: zapcore.SecondsDurationEncoder,
			EncodeCaller:   zapcore.ShortCallerEncoder,
		},
		OutputPaths:      []string{"stdout"},
		ErrorOutputPaths: []string{"stderr"},
	}

	return config.Build()
}
