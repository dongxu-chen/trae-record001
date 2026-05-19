package dns

import (
	"time"

	"github.com/go-acme/lego/v4/challenge"
)

type providerAdapter struct {
	provider Provider
}

func (a *providerAdapter) Present(domain, token, keyAuth string) error {
	return a.provider.Present(domain, token, keyAuth)
}

func (a *providerAdapter) CleanUp(domain, token, keyAuth string) error {
	return a.provider.CleanUp(domain, token, keyAuth)
}

func (a *providerAdapter) Timeout() (timeout, interval time.Duration) {
	return a.provider.Timeout()
}

func NewChallengeProvider(provider Provider) challenge.Provider {
	return &providerAdapter{
		provider: provider,
	}
}
