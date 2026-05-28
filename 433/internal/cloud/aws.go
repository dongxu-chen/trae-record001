package cloud

import (
	"context"
	"fmt"
	"time"

	"k8s-cost-allocation/internal/config"

	"github.com/aws/aws-sdk-go-v2/aws"
	awsConfig "github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/credentials"
	"github.com/aws/aws-sdk-go-v2/service/costexplorer"
	"github.com/aws/aws-sdk-go-v2/service/costexplorer/types"
)

type AWSBillingClient struct {
	cfg    config.CloudConfig
	client   *costexplorer.Client
}

type BillingCost struct {
	StartDate string  `json:"startDate"`
	EndDate   string  `json:"endDate"`
	TotalCost float64 `json:"totalCost"`
	Currency  string  `json:"currency"`
}

type ServiceCost struct {
	ServiceName string  `json:"serviceName"`
	Cost        float64 `json:"cost"`
	Percentage  float64 `json:"percentage"`
}

func NewAWSBillingClient(cfg config.CloudConfig) (*AWSBillingClient, error) {
	var awsCfg aws.Config
	var err error

	if cfg.AWS.AccessKey != "" && cfg.AWS.SecretKey != "" {
		awsCfg, err = awsConfig.LoadDefaultConfig(context.TODO(),
			awsConfig.WithRegion(cfg.Region),
			awsConfig.WithCredentialsProvider(
				credentials.NewStaticCredentialsProvider(cfg.AWS.AccessKey, cfg.AWS.SecretKey, ""),
			),
		)
	} else {
		awsCfg, err = awsConfig.LoadDefaultConfig(context.TODO(),
			awsConfig.WithRegion(cfg.Region),
		)
	}

	if err != nil {
		return nil, fmt.Errorf("failed to load AWS config: %w", err)
	}

	client := costexplorer.NewFromConfig(awsCfg)
	return &AWSBillingClient{
		cfg:    cfg,
		client:   client,
	}, nil
}

func (a *AWSBillingClient) GetCostAndUsage(ctx context.Context, start, end time.Time, granularity string) (*BillingCost, error) {
	input := &costexplorer.GetCostAndUsageInput{
		TimePeriod: &types.DateInterval{
			Start: aws.String(start.Format("2006-01-02")),
			End:   aws.String(end.Format("2006-01-02")),
		},
		Granularity: types.Granularity(granularity),
		Metrics:     []string{"UnblendedCost"},
	}

	result, err := a.client.GetCostAndUsage(ctx, input)
	if err != nil {
		return nil, fmt.Errorf("failed to get cost and usage: %w", err)
	}

	var totalCost float64
	for _, resultByTime := range result.ResultsByTime {
		for _, group := range resultByTime.Groups {
			for _, metric := range group.Metrics {
				if metric.Amount != nil {
					var amount := 0.0
					fmt.Sscanf(*metric.Amount, "%f", &amount)
					totalCost += amount
				}
			}
		}
	}

	return &BillingCost{
		StartDate: start.Format("2006-01-02"),
		EndDate:   end.Format("2006-01-02"),
		TotalCost: totalCost,
		Currency:  "USD",
	}, nil
}

func (a *AWSBillingClient) GetCostByService(ctx context.Context, start, end time.Time) ([]ServiceCost, error) {
	input := &costexplorer.GetCostAndUsageInput{
		TimePeriod: &types.DateInterval{
			Start: aws.String(start.Format("2006-01-02")),
			End:   aws.String(end.Format("2006-01-02")),
		},
		Granularity: types.GranularityMonthly,
		Metrics:     []string{"UnblendedCost"},
		GroupBy: []types.GroupDefinition{
			{
				Type: types.GroupDefinitionTypeDimension,
				Key:  aws.String("SERVICE"),
			},
		},
	}

	result, err := a.client.GetCostAndUsage(ctx, input)
	if err != nil {
		return nil, fmt.Errorf("failed to get cost by service: %w", err)
	}

	var totalCost float64
	serviceCosts := make(map[string]float64)

	for _, resultByTime := range result.ResultsByTime {
		for _, group := range resultByTime.Groups {
			serviceName := "Unknown"
			if len(group.Keys) > 0 {
				serviceName = group.Keys[0]
			}
			for _, metric := range group.Metrics {
				if metric.Amount != nil {
					var amount float64
					fmt.Sscanf(*metric.Amount, "%f", &amount)
					serviceCosts[serviceName] += amount
					totalCost += amount
				}
			}
		}
	}

	var results []ServiceCost
	for service, cost := range serviceCosts {
		percentage := 0.0
		if totalCost > 0 {
			percentage = (cost / totalCost) * 100
		}
		results = append(results, ServiceCost{
			ServiceName: service,
			Cost:        cost,
			Percentage:  percentage,
		})
	}

	return results, nil
}

func (a *AWSBillingClient) GetCostForecast(ctx context.Context, start, end time.Time) (*BillingCost, error) {
	input := &costexplorer.GetCostForecastInput{
		TimePeriod: &types.DateInterval{
			Start: aws.String(start.Format("2006-01-02")),
			End:   aws.String(end.Format("2006-01-02")),
		},
		Metric: types.MetricUnblendedCost,
		Granularity: types.GranularityMonthly,
	}

	result, err := a.client.GetCostForecast(ctx, input)
	if err != nil {
		return nil, fmt.Errorf("failed to get cost forecast: %w", err)
	}

	var forecastedCost := 0.0
	if result.Total != nil && result.Total.MeanValue != nil {
		fmt.Sscanf(*result.Total.MeanValue, "%f", &forecastedCost)
	}

	return &BillingCost{
		StartDate: start.Format("2006-01-02"),
		EndDate:   end.Format("2006-01-02"),
		TotalCost: forecastedCost,
		Currency:  "USD",
	}, nil
}
