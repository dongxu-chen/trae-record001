package main

import (
	"context"
	"flag"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"ssl-monitor/config"
	"ssl-monitor/cron"
	"ssl-monitor/handlers"
	"ssl-monitor/services"
	"ssl-monitor/storage"
	"syscall"
	"time"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"go.uber.org/zap"
)

func main() {
	configPath := flag.String("config", "", "配置文件路径")
	flag.Parse()

	config.Load(*configPath)
	storage.Init()

	gin.SetMode(config.Cfg.Server.Mode)
	r := gin.Default()

	r.Use(cors.New(cors.Config{
		AllowOrigins:     []string{"*"},
		AllowMethods:     []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"},
		AllowHeaders:     []string{"Origin", "Content-Type", "Authorization"},
		ExposeHeaders:    []string{"Content-Length"},
		AllowCredentials: true,
		MaxAge:           12 * time.Hour,
	}))

	ruleSvc := services.NewRuleLibraryService()
	dnsSvc := services.NewDNSService()
	alertSvc := services.NewAlertService()
	certAnalysisSvc := services.NewCertAnalysisService(alertSvc)
	sslSvc := services.NewSSLCertService(ruleSvc, dnsSvc, certAnalysisSvc)
	domainHandler := handlers.NewDomainHandler(sslSvc, alertSvc, ruleSvc, dnsSvc, certAnalysisSvc)

	api := r.Group("/api")
	{
		api.GET("/dashboard", domainHandler.GetDashboard)

		api.GET("/domains", domainHandler.GetDomains)
		api.POST("/domains", domainHandler.CreateDomain)
		api.PUT("/domains/:id", domainHandler.UpdateDomain)
		api.DELETE("/domains/:id", domainHandler.DeleteDomain)
		api.GET("/domains/:id", domainHandler.GetDomainWithCert)
		api.POST("/domains/:id/check", domainHandler.CheckDomain)
		api.PUT("/domains/:id/toggle", domainHandler.ToggleDomain)
		api.POST("/domains/import", domainHandler.ImportDomains)
		api.POST("/domains/batch", domainHandler.BatchCreateDomains)
		api.GET("/tags", domainHandler.GetTags)

		api.GET("/certs", domainHandler.GetCertRecords)
		api.GET("/certs/:domain_id/history", domainHandler.GetCertHistory)

		api.GET("/report", domainHandler.GetReport)
		api.GET("/report/export", domainHandler.ExportReport)

		api.GET("/alerts", domainHandler.GetAlertLogs)
		api.POST("/alerts/test", domainHandler.SendTestAlert)

		api.GET("/dns/records", domainHandler.GetDNSRecords)
		api.GET("/dns/subdomains", domainHandler.GetSubdomains)
		api.POST("/dns/scan", domainHandler.ScanDNS)
		api.POST("/dns/subdomains/:id/promote", domainHandler.PromoteSubdomain)
		api.POST("/dns/subdomains/:id", domainHandler.DeleteSubdomainRecord)
		api.GET("/dns/stats", domainHandler.GetDNSStats)

		api.GET("/rules", domainHandler.GetRules)
		api.POST("/rules/update", domainHandler.UpdateRules)
		api.GET("/rules/logs", domainHandler.GetRuleUpdateLogs)
		api.POST("/rules", domainHandler.AddRule)
		api.PUT("/rules/:id", domainHandler.UpdateRule)
		api.DELETE("/rules/:id", domainHandler.DeleteRule)
		api.GET("/rules/version", domainHandler.GetRuleVersion)
		api.POST("/rules/export", domainHandler.ExportRules)
		api.POST("/rules/import", domainHandler.ImportRules)

		api.GET("/scan/config", domainHandler.GetScanConfig)

		api.GET("/certs/:domain_id/chain", domainHandler.GetCertChainInfo)
		api.GET("/certs/:domain_id/compare", domainHandler.CompareCertWithPrevious)
		api.GET("/certs/:domain_id/changes", domainHandler.GetCertChanges)
		api.GET("/certs/unlogged", domainHandler.GetUnloggedCerts)
		api.GET("/certs/incomplete-chain", domainHandler.GetIncompleteChainCerts)
	}

	srv := &http.Server{
		Addr:         fmt.Sprintf(":%d", config.Cfg.Server.Port),
		Handler:      r,
		ReadTimeout:  time.Duration(config.Cfg.Server.ReadTimeout) * time.Second,
		WriteTimeout: time.Duration(config.Cfg.Server.WriteTimeout) * time.Second,
	}

	cronSvc := cron.NewCronService(sslSvc, alertSvc, ruleSvc, dnsSvc)
	cronSvc.Start()

	go func() {
		config.Logger.Info("SSL证书监控服务启动",
			zap.Int("port", config.Cfg.Server.Port),
			zap.String("mode", config.Cfg.Server.Mode))

		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			config.Logger.Fatal("服务启动失败", zap.Error(err))
		}
	}()

	go func() {
		time.Sleep(2 * time.Second)
		cronSvc.RunNow()
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	config.Logger.Info("正在关闭服务...")

	cronSvc.Stop()

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	if err := srv.Shutdown(ctx); err != nil {
		config.Logger.Fatal("服务强制关闭", zap.Error(err))
	}

	config.Logger.Info("服务已关闭")
}
