package com.tracing.sampling.store;

import com.tracing.sampling.model.SamplingDecisionRecord;

public interface SamplingConfigStore {

    long getAverageLatency(String endpointKey);

    void updateLatencyStats(String endpointKey, long latency);

    double getEndpointSampleRateMultiplier(String endpointKey);

    void setEndpointSampleRateMultiplier(String endpointKey, double multiplier);

    void recordSamplingDecision(SamplingDecisionRecord record);

    double getCurrentSampleRate();

    void updateCurrentSampleRate(double rate);

    double getGlobalTargetSampleRate();

    void setGlobalTargetSampleRate(double rate);
}
