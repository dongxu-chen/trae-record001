package com.oauth2.monitor.metrics;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.DistributionSummary;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import org.springframework.stereotype.Component;

import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

@Component
public class OAuth2Metrics {

    private final MeterRegistry meterRegistry;

    private final Counter authorizationCodeRequestsTotal;
    private final Counter authorizationCodeRequestsSuccess;
    private final Counter authorizationCodeRequestsFailed;
    private final Counter tokenRequestsTotal;
    private final Counter tokenRequestsSuccess;
    private final Counter tokenRequestsFailed;
    private final Counter refreshTokenRequestsTotal;
    private final Counter refreshTokenRequestsSuccess;
    private final Counter refreshTokenRequestsFailed;
    private final Counter revokedTokensTotal;
    private final Counter expiredTokensTotal;
    private final Counter invalidTokenAttempts;

    private final Timer authorizationCodeLatency;
    private final Timer tokenIssueLatency;
    private final Timer tokenValidationLatency;

    private final DistributionSummary tokenLifetimeDistribution;

    private final ConcurrentHashMap<String, Counter> errorCodeCounters = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, Counter> grantTypeCounters = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, Counter> clientCounters = new ConcurrentHashMap<>();

    private final AtomicLong activeAccessTokens = new AtomicLong(0);
    private final AtomicLong activeRefreshTokens = new AtomicLong(0);
    private final AtomicLong totalAuthorizationCodesIssued = new AtomicLong(0);
    private final AtomicLong totalTokensIssued = new AtomicLong(0);

    public OAuth2Metrics(MeterRegistry meterRegistry) {
        this.meterRegistry = meterRegistry;

        this.authorizationCodeRequestsTotal = Counter.builder("oauth2.authorization_code.requests_total")
                .description("Total number of authorization code requests")
                .register(meterRegistry);

        this.authorizationCodeRequestsSuccess = Counter.builder("oauth2.authorization_code.requests_success")
                .description("Successful authorization code requests")
                .register(meterRegistry);

        this.authorizationCodeRequestsFailed = Counter.builder("oauth2.authorization_code.requests_failed")
                .description("Failed authorization code requests")
                .register(meterRegistry);

        this.tokenRequestsTotal = Counter.builder("oauth2.token.requests_total")
                .description("Total number of token requests")
                .register(meterRegistry);

        this.tokenRequestsSuccess = Counter.builder("oauth2.token.requests_success")
                .description("Successful token requests")
                .register(meterRegistry);

        this.tokenRequestsFailed = Counter.builder("oauth2.token.requests_failed")
                .description("Failed token requests")
                .register(meterRegistry);

        this.refreshTokenRequestsTotal = Counter.builder("oauth2.refresh_token.requests_total")
                .description("Total number of refresh token requests")
                .register(meterRegistry);

        this.refreshTokenRequestsSuccess = Counter.builder("oauth2.refresh_token.requests_success")
                .description("Successful refresh token requests")
                .register(meterRegistry);

        this.refreshTokenRequestsFailed = Counter.builder("oauth2.refresh_token.requests_failed")
                .description("Failed refresh token requests")
                .register(meterRegistry);

        this.revokedTokensTotal = Counter.builder("oauth2.tokens.revoked_total")
                .description("Total number of revoked tokens")
                .register(meterRegistry);

        this.expiredTokensTotal = Counter.builder("oauth2.tokens.expired_total")
                .description("Total number of expired tokens")
                .register(meterRegistry);

        this.invalidTokenAttempts = Counter.builder("oauth2.tokens.invalid_attempts_total")
                .description("Total number of invalid token usage attempts")
                .register(meterRegistry);

        this.authorizationCodeLatency = Timer.builder("oauth2.authorization_code.latency")
                .description("Latency of authorization code issuance")
                .publishPercentiles(0.5, 0.75, 0.95, 0.99)
                .register(meterRegistry);

        this.tokenIssueLatency = Timer.builder("oauth2.token.issue_latency")
                .description("Latency of token issuance")
                .publishPercentiles(0.5, 0.75, 0.95, 0.99)
                .register(meterRegistry);

        this.tokenValidationLatency = Timer.builder("oauth2.token.validation_latency")
                .description("Latency of token validation")
                .publishPercentiles(0.5, 0.75, 0.95, 0.99)
                .register(meterRegistry);

        this.tokenLifetimeDistribution = DistributionSummary.builder("oauth2.token.lifetime_seconds")
                .description("Distribution of token lifetimes")
                .publishPercentiles(0.5, 0.75, 0.95, 0.99)
                .register(meterRegistry);

        meterRegistry.gauge("oauth2.tokens.active_access", activeAccessTokens, AtomicLong::get);
        meterRegistry.gauge("oauth2.tokens.active_refresh", activeRefreshTokens, AtomicLong::get);
        meterRegistry.gauge("oauth2.authorization_codes.total_issued", totalAuthorizationCodesIssued, AtomicLong::get);
        meterRegistry.gauge("oauth2.tokens.total_issued", totalTokensIssued, AtomicLong::get);
    }

    public void recordAuthorizationCodeRequest(boolean success, String errorCode, String clientId) {
        authorizationCodeRequestsTotal.increment();
        if (success) {
            authorizationCodeRequestsSuccess.increment();
            totalAuthorizationCodesIssued.incrementAndGet();
        } else {
            authorizationCodeRequestsFailed.increment();
            recordErrorCode(errorCode);
        }
        recordClientRequest(clientId);
    }

    public void recordTokenRequest(String grantType, boolean success, String errorCode, String clientId) {
        tokenRequestsTotal.increment();
        if (success) {
            tokenRequestsSuccess.increment();
            totalTokensIssued.incrementAndGet();
            activeAccessTokens.incrementAndGet();
        } else {
            tokenRequestsFailed.increment();
            recordErrorCode(errorCode);
        }
        recordGrantType(grantType);
        recordClientRequest(clientId);
    }

    public void recordRefreshTokenRequest(boolean success, String errorCode, String clientId) {
        refreshTokenRequestsTotal.increment();
        if (success) {
            refreshTokenRequestsSuccess.increment();
            totalTokensIssued.incrementAndGet();
        } else {
            refreshTokenRequestsFailed.increment();
            recordErrorCode(errorCode);
        }
        recordClientRequest(clientId);
    }

    public void recordTokenRevoked() {
        revokedTokensTotal.increment();
        activeAccessTokens.decrementAndGet();
    }

    public void recordTokenExpired() {
        expiredTokensTotal.increment();
        activeAccessTokens.decrementAndGet();
    }

    public void recordInvalidTokenAttempt() {
        invalidTokenAttempts.increment();
    }

    private void recordErrorCode(String errorCode) {
        if (errorCode != null && !errorCode.isEmpty()) {
            errorCodeCounters.computeIfAbsent(errorCode, code ->
                    Counter.builder("oauth2.errors.total")
                            .description("OAuth2 errors by error code")
                            .tag("error_code", code)
                            .register(meterRegistry)
            ).increment();
        }
    }

    private void recordGrantType(String grantType) {
        if (grantType != null && !grantType.isEmpty()) {
            grantTypeCounters.computeIfAbsent(grantType, type ->
                    Counter.builder("oauth2.grant_types.total")
                            .description("Token requests by grant type")
                            .tag("grant_type", type)
                            .register(meterRegistry)
            ).increment();
        }
    }

    private void recordClientRequest(String clientId) {
        if (clientId != null && !clientId.isEmpty()) {
            clientCounters.computeIfAbsent(clientId, client ->
                    Counter.builder("oauth2.clients.requests_total")
                            .description("Requests by client ID")
                            .tag("client_id", client)
                            .register(meterRegistry)
            ).increment();
        }
    }

    public Timer.Sample startAuthorizationCodeTimer() {
        return Timer.start(meterRegistry);
    }

    public void stopAuthorizationCodeTimer(Timer.Sample sample) {
        sample.stop(authorizationCodeLatency);
    }

    public Timer.Sample startTokenIssueTimer() {
        return Timer.start(meterRegistry);
    }

    public void stopTokenIssueTimer(Timer.Sample sample) {
        sample.stop(tokenIssueLatency);
    }

    public Timer.Sample startTokenValidationTimer() {
        return Timer.start(meterRegistry);
    }

    public void stopTokenValidationTimer(Timer.Sample sample) {
        sample.stop(tokenValidationLatency);
    }

    public void recordTokenLifetime(long lifetimeSeconds) {
        tokenLifetimeDistribution.record(lifetimeSeconds);
    }

    public double getAuthorizationCodeSuccessRate() {
        double total = authorizationCodeRequestsTotal.count();
        return total == 0 ? 100.0 : (authorizationCodeRequestsSuccess.count() / total) * 100;
    }

    public double getTokenSuccessRate() {
        double total = tokenRequestsTotal.count();
        return total == 0 ? 100.0 : (tokenRequestsSuccess.count() / total) * 100;
    }

    public double getRefreshTokenSuccessRate() {
        double total = refreshTokenRequestsTotal.count();
        return total == 0 ? 100.0 : (refreshTokenRequestsSuccess.count() / total) * 100;
    }

    public MeterRegistry getMeterRegistry() {
        return meterRegistry;
    }
}
