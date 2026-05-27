package cron

import (
	"ssl-monitor/config"
	"ssl-monitor/services"

	"github.com/robfig/cron/v3"
	"go.uber.org/zap"
)

type CronService struct {
	cron      *cron.Cron
	sslSvc    *services.SSLCertService
	alertSvc  *services.AlertService
	ruleSvc   *services.RuleLibraryService
	dnsSvc    *services.DNSService
}

func NewCronService(sslSvc *services.SSLCertService, alertSvc *services.AlertService, ruleSvc *services.RuleLibraryService, dnsSvc *services.DNSService) *CronService {
	return &CronService{
		cron:     cron.New(),
		sslSvc:   sslSvc,
		alertSvc: alertSvc,
		ruleSvc:  ruleSvc,
		dnsSvc:   dnsSvc,
	}
}

func (s *CronService) Start() {
	s.cron.AddFunc(config.Cfg.Cron.ScanInterval, func() {
		config.Logger.Info("开始定时SSL证书扫描任务")

		if config.Cfg.DNS.Enabled {
			go s.dnsSvc.ScanAllDomains()
		}

		results := s.sslSvc.CheckAllDomains()
		if results != nil {
			s.alertSvc.SendAlertsForResults(results)
		}

		config.Logger.Info("定时SSL证书扫描任务完成", zap.Int("count", len(results)))
	})

	if config.Cfg.RuleLibrary.AutoUpdate {
		s.cron.AddFunc(config.Cfg.Cron.RulesUpdateInterval, func() {
			config.Logger.Info("开始更新算法规则库")
			_, err := s.ruleSvc.UpdateRules()
			if err != nil {
				config.Logger.Warn("规则库更新失败", zap.Error(err))
			} else {
				config.Logger.Info("规则库更新成功")
			}
		})
		config.Logger.Info("规则库自动更新已启用", zap.String("interval", config.Cfg.Cron.RulesUpdateInterval))
	}

	s.cron.Start()
	config.Logger.Info("定时任务已启动",
		zap.String("scan_interval", config.Cfg.Cron.ScanInterval),
		zap.Int("max_concurrent", config.Cfg.Scan.MaxConcurrent),
		zap.Bool("random_delay", config.Cfg.Scan.RandomizeDelay))
}

func (s *CronService) Stop() {
	s.cron.Stop()
	config.Logger.Info("定时任务已停止")
}

func (s *CronService) RunNow() {
	config.Logger.Info("手动触发SSL证书扫描")

	if config.Cfg.DNS.Enabled {
		go s.dnsSvc.ScanAllDomains()
	}

	results := s.sslSvc.CheckAllDomains()
	if results != nil {
		s.alertSvc.SendAlertsForResults(results)
	}

	config.Logger.Info("手动SSL证书扫描完成", zap.Int("count", len(results)))
}

func (s *CronService) UpdateRulesNow() {
	config.Logger.Info("手动触发规则库更新")
	log, err := s.ruleSvc.UpdateRules()
	if err != nil {
		config.Logger.Warn("规则库更新失败", zap.Error(err))
	} else {
		config.Logger.Info("规则库更新成功",
			zap.Int("added", log.AddedRules),
			zap.Int("updated", log.UpdatedRules),
			zap.Int("total", log.TotalRules))
	}
}

func (s *CronService) ScanDNSNow() {
	config.Logger.Info("手动触发DNS扫描")
	s.dnsSvc.ScanAllDomains()
	config.Logger.Info("DNS扫描完成")
}
