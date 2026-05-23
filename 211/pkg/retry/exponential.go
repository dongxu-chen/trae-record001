package retry

import (
	"context"
	"math"
	"time"
)

const (
	DefaultBaseMultiplier = 2.0
	MaxDelaySeconds       = 3600
	MaxDelayDuration      = time.Hour
)

type Config struct {
	MaxAttempts int
	BaseDelay   time.Duration
	MaxDelay    time.Duration
	Multiplier  float64
}

func DefaultConfig() Config {
	return Config{
		MaxAttempts: 5,
		BaseDelay:   1 * time.Second,
		MaxDelay:    MaxDelayDuration,
		Multiplier:  DefaultBaseMultiplier,
	}
}

type RetryFunc func(ctx context.Context) error

func Do(ctx context.Context, config Config, fn RetryFunc) error {
	var lastErr error

	for attempt := 0; attempt < config.MaxAttempts; attempt++ {
		if err := ctx.Err(); err != nil {
			return err
		}

		err := fn(ctx)
		if err == nil {
			return nil
		}
		lastErr = err

		if attempt == config.MaxAttempts-1 {
			break
		}

		delay := calculateDelay(attempt, config)
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-time.After(delay):
		}
	}

	return lastErr
}

func calculateDelay(attempt int, config Config) time.Duration {
	delay := float64(config.BaseDelay) * math.Pow(config.Multiplier, float64(attempt))
	if delay > float64(config.MaxDelay) {
		delay = float64(config.MaxDelay)
	}
	return time.Duration(delay)
}

func CalculateNextRetryTime(attempt int, baseDelaySec int) time.Time {
	return CalculateNextRetryTimeWithBase(attempt, baseDelaySec, DefaultBaseMultiplier)
}

func CalculateNextRetryTimeWithBase(attempt int, baseDelaySec int, multiplier float64) time.Time {
	delay := float64(baseDelaySec) * math.Pow(multiplier, float64(attempt))
	if delay > MaxDelaySeconds {
		delay = MaxDelaySeconds
	}
	return time.Now().Add(time.Duration(delay) * time.Second)
}

func CalculateDelay(attempt int, baseDelay time.Duration) time.Duration {
	return CalculateDelayWithBase(attempt, baseDelay, DefaultBaseMultiplier)
}

func CalculateDelayWithBase(attempt int, baseDelay time.Duration, multiplier float64) time.Duration {
	delay := float64(baseDelay) * math.Pow(multiplier, float64(attempt))
	if delay > float64(MaxDelayDuration) {
		delay = float64(MaxDelayDuration)
	}
	return time.Duration(delay)
}

func GetBackoffSequence(maxAttempts int, baseDelay time.Duration) []time.Duration {
	sequence := make([]time.Duration, maxAttempts)
	for i := 0; i < maxAttempts; i++ {
		sequence[i] = CalculateDelay(i, baseDelay)
	}
	return sequence
}
