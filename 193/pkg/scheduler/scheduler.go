package scheduler

import (
	"context"
	"fmt"
	"sync"

	"github.com/robfig/cron/v3"
	"github.com/sirupsen/logrus"

	"k8s-auditor/pkg/audit"
	"k8s-auditor/pkg/reporter"
	"k8s-auditor/pkg/webhook"
)

type Scheduler struct {
	cron      *cron.Cron
	auditor   *audit.Auditor
	reporter  *reporter.Reporter
	webhook   *webhook.WebhookNotifier
	logger    *logrus.Logger
	schedule  string
	running   bool
	mu        sync.Mutex
}

func New(auditor *audit.Auditor, rep *reporter.Reporter, wh *webhook.WebhookNotifier, schedule string) *Scheduler {
	return &Scheduler{
		cron:     cron.New(cron.WithSeconds()),
		auditor:  auditor,
		reporter: rep,
		webhook:  wh,
		logger:   logrus.New(),
		schedule: schedule,
		running:  false,
	}
}

func (s *Scheduler) Start(ctx context.Context) error {
	s.logger.Infof("启动定时审计调度器，调度规则: %s", s.schedule)

	_, err := s.cron.AddFunc(s.schedule, func() {
		s.runAudit(ctx)
	})
	if err != nil {
		return fmt.Errorf("failed to add cron job: %w", err)
	}

	s.cron.Start()

	<-ctx.Done()
	s.cron.Stop()
	s.logger.Info("调度器已停止")

	return nil
}

func (s *Scheduler) runAudit(ctx context.Context) {
	s.mu.Lock()
	if s.running {
		s.logger.Warn("上一次审计仍在执行中，跳过本次审计")
		s.mu.Unlock()
		return
	}
	s.running = true
	s.mu.Unlock()

	defer func() {
		s.mu.Lock()
		s.running = false
		s.mu.Unlock()
	}()

	s.logger.Info("开始执行定时审计...")

	report, err := s.auditor.Run(ctx)
	if err != nil {
		s.logger.Errorf("审计执行失败: %v", err)
		return
	}

	jsonPath, yamlPath, err := s.reporter.GenerateReport(report)
	if err != nil {
		s.logger.Errorf("生成审计报告失败: %v", err)
	} else {
		s.logger.Infof("审计报告已生成: JSON=%s, YAML=%s", jsonPath, yamlPath)
	}

	textPath, err := s.reporter.SaveTextReport(report)
	if err != nil {
		s.logger.Errorf("保存文本报告失败: %v", err)
	} else {
		s.logger.Infof("文本审计报告已保存: %s", textPath)
	}

	if s.webhook != nil && s.webhook.Enabled() {
		if err := s.webhook.Send(report); err != nil {
			s.logger.Errorf("发送 Webhook 通知失败: %v", err)
		} else {
			s.logger.Info("Webhook 通知已发送")
		}
	}

	s.logger.Infof("审计完成，共发现 %d 个违规项", len(report.Violations))
}

func (s *Scheduler) RunOnce(ctx context.Context) (*audit.AuditReport, error) {
	s.logger.Info("执行单次审计...")
	return s.auditor.Run(ctx)
}
