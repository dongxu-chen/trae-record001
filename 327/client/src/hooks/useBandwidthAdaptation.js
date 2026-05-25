import { useEffect, useCallback, useRef } from 'react';
import useMeetingStore from '../store/useMeetingStore';
import { RESOLUTION_LEVELS, BANDWIDTH_THRESHOLDS } from '../config/webrtcConfig';

class BandwidthPredictor {
  constructor(alpha = 0.3, historySize = 30) {
    this.alpha = alpha;
    this.historySize = historySize;
    this.bitrateHistory = [];
    this.packetLossHistory = [];
    this.rttHistory = [];
    this.ewmaBitrate = 0;
    this.ewmaPacketLoss = 0;
    this.ewmaRtt = 0;
    this.trend = 0;
    this.lastPrediction = 0;
    this.predictionConfidence = 0;
  }

  addSample(bitrate, packetLoss, rtt) {
    const timestamp = Date.now();
    
    this.bitrateHistory.push({ bitrate, timestamp });
    this.packetLossHistory.push({ packetLoss, timestamp });
    this.rttHistory.push({ rtt, timestamp });

    if (this.bitrateHistory.length > this.historySize) {
      this.bitrateHistory.shift();
      this.packetLossHistory.shift();
      this.rttHistory.shift();
    }

    this._updateEWMA();
    this._updateTrend();
    this._updateConfidence();
  }

  _updateEWMA() {
    if (this.bitrateHistory.length === 0) return;

    this.ewmaBitrate = this.bitrateHistory[0].bitrate;
    for (let i = 1; i < this.bitrateHistory.length; i++) {
      this.ewmaBitrate = this.alpha * this.bitrateHistory[i].bitrate + 
                        (1 - this.alpha) * this.ewmaBitrate;
    }

    this.ewmaPacketLoss = this.packetLossHistory[0].packetLoss;
    for (let i = 1; i < this.packetLossHistory.length; i++) {
      this.ewmaPacketLoss = this.alpha * this.packetLossHistory[i].packetLoss + 
                           (1 - this.alpha) * this.ewmaPacketLoss;
    }

    if (this.rttHistory.length > 0) {
      this.ewmaRtt = this.rttHistory[0].rtt;
      for (let i = 1; i < this.rttHistory.length; i++) {
        this.ewmaRtt = this.alpha * this.rttHistory[i].rtt + 
                      (1 - this.alpha) * this.ewmaRtt;
      }
    }
  }

  _updateTrend() {
    if (this.bitrateHistory.length < 5) {
      this.trend = 0;
      return;
    }

    const recent = this.bitrateHistory.slice(-5);
    let sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0;
    const n = recent.length;

    recent.forEach((item, i) => {
      const x = i;
      const y = item.bitrate;
      sumX += x;
      sumY += y;
      sumXY += x * y;
      sumX2 += x * x;
    });

    const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
    this.trend = slope;
  }

  _updateConfidence() {
    if (this.bitrateHistory.length < 3) {
      this.predictionConfidence = 0;
      return;
    }

    const mean = this.ewmaBitrate;
    const variance = this.bitrateHistory.reduce((sum, item) => {
      return sum + Math.pow(item.bitrate - mean, 2);
    }, 0) / this.bitrateHistory.length;

    const stdDev = Math.sqrt(variance);
    const coefficientOfVariation = stdDev / (mean || 1);

    this.predictionConfidence = Math.max(0, 1 - coefficientOfVariation * 0.5);
  }

  predictFutureBandwidth(secondsAhead = 5) {
    if (this.bitrateHistory.length < 3) {
      return this.ewmaBitrate || BANDWIDTH_THRESHOLDS.good;
    }

    const predictedBitrate = this.ewmaBitrate + this.trend * secondsAhead;
    const stabilityFactor = this.predictionConfidence;

    const conservativePrediction = this.ewmaBitrate * stabilityFactor + 
                                  predictedBitrate * (1 - stabilityFactor);

    const headroom = this._calculateHeadroom();
    const finalPrediction = conservativePrediction * headroom;

    this.lastPrediction = finalPrediction;
    return finalPrediction;
  }

  _calculateHeadroom() {
    let headroom = 1.0;

    if (this.ewmaPacketLoss > 5) {
      headroom *= 0.6;
    } else if (this.ewmaPacketLoss > 3) {
      headroom *= 0.75;
    } else if (this.ewmaPacketLoss > 1) {
      headroom *= 0.85;
    }

    if (this.ewmaRtt > 300) {
      headroom *= 0.7;
    } else if (this.ewmaRtt > 200) {
      headroom *= 0.85;
    } else if (this.ewmaRtt > 100) {
      headroom *= 0.95;
    }

    if (this.trend < -50) {
      headroom *= 0.7;
    } else if (this.trend < -20) {
      headroom *= 0.85;
    } else if (this.trend > 50) {
      headroom *= 1.1;
    }

    return Math.max(0.3, Math.min(1.2, headroom));
  }

  getPredictedQuality() {
    const predictedBandwidth = this.predictFutureBandwidth();
    const packetLoss = this.ewmaPacketLoss;
    const rtt = this.ewmaRtt;

    if (predictedBandwidth > BANDWIDTH_THRESHOLDS.excellent && packetLoss < 1 && rtt < 100) {
      return 'excellent';
    } else if (predictedBandwidth > BANDWIDTH_THRESHOLDS.good && packetLoss < 3 && rtt < 200) {
      return 'good';
    } else if (predictedBandwidth > BANDWIDTH_THRESHOLDS.fair && packetLoss < 5 && rtt < 300) {
      return 'fair';
    }
    return 'poor';
  }

  getRecommendedResolution(currentLevelIndex) {
    const predictedBandwidth = this.predictFutureBandwidth();
    const predictedQuality = this.getPredictedQuality();

    let recommendedLevel = currentLevelIndex;

    if (predictedQuality === 'excellent' && currentLevelIndex < RESOLUTION_LEVELS.length - 1) {
      recommendedLevel = currentLevelIndex + 1;
    } else if (predictedQuality === 'good' && currentLevelIndex < RESOLUTION_LEVELS.length - 1) {
      if (predictedBandwidth > RESOLUTION_LEVELS[currentLevelIndex + 1]?.bitrate * 0.9) {
        recommendedLevel = currentLevelIndex + 1;
      }
    } else if (predictedQuality === 'poor' && currentLevelIndex > 0) {
      recommendedLevel = Math.max(0, currentLevelIndex - 1);
    } else if (predictedQuality === 'fair') {
      if (currentLevelIndex > 1) {
        recommendedLevel = currentLevelIndex - 1;
      }
    }

    for (let i = RESOLUTION_LEVELS.length - 1; i >= 0; i--) {
      if (predictedBandwidth >= RESOLUTION_LEVELS[i].bitrate * 0.8) {
        recommendedLevel = Math.min(recommendedLevel, i);
        break;
      }
    }

    return {
      level: recommendedLevel,
      confidence: this.predictionConfidence,
      predictedBandwidth,
      predictedQuality
    };
  }

  getStats() {
    return {
      ewmaBitrate: this.ewmaBitrate,
      ewmaPacketLoss: this.ewmaPacketLoss,
      ewmaRtt: this.ewmaRtt,
      trend: this.trend,
      confidence: this.predictionConfidence,
      lastPrediction: this.lastPrediction,
      historySize: this.bitrateHistory.length
    };
  }

  reset() {
    this.bitrateHistory = [];
    this.packetLossHistory = [];
    this.rttHistory = [];
    this.ewmaBitrate = 0;
    this.ewmaPacketLoss = 0;
    this.ewmaRtt = 0;
    this.trend = 0;
    this.lastPrediction = 0;
    this.predictionConfidence = 0;
  }
}

const useBandwidthAdaptation = (peers, changeResolution) => {
  const {
    connectionQuality,
    currentResolution,
    setConnectionQuality
  } = useMeetingStore();

  const predictorRef = useRef(null);
  const currentLevelIndexRef = useRef(2);
  const adaptationCooldownRef = useRef(false);
  const lastAdaptationTimeRef = useRef(0);
  const statsRef = useRef(new Map());

  if (!predictorRef.current) {
    predictorRef.current = new BandwidthPredictor(0.3, 30);
  }

  const getCurrentResolutionLevel = useCallback(() => {
    const index = RESOLUTION_LEVELS.findIndex(
      level => level.width === currentResolution.width
    );
    return index >= 0 ? index : 2;
  }, [currentResolution]);

  const getPeerStats = useCallback(async (peer, peerId) => {
    if (!peer || !peer._pc || peer.destroyed) return null;

    try {
      const stats = await peer._pc.getStats(null);
      let totalBytes = 0;
      let totalPacketsLost = 0;
      let totalPackets = 0;
      let rtt = 0;
      let rttCount = 0;

      stats.forEach(report => {
        if (report.type === 'inbound-rtp' && report.mediaType === 'video') {
          totalBytes += report.bytesReceived || 0;
          totalPacketsLost += report.packetsLost || 0;
          totalPackets += report.packetsReceived || 0;
        }
        if (report.type === 'candidate-pair' && report.state === 'succeeded') {
          if (report.currentRoundTripTime) {
            rtt += report.currentRoundTripTime * 1000;
            rttCount++;
          }
        }
      });

      const avgRtt = rttCount > 0 ? rtt / rttCount : 0;
      const packetLossPercent = totalPackets > 0 ? (totalPacketsLost / totalPackets) * 100 : 0;

      const prevStats = statsRef.current.get(peerId) || { bytes: 0, timestamp: Date.now() };
      const timeDelta = (Date.now() - prevStats.timestamp) / 1000;
      const bitrate = timeDelta > 0 ? ((totalBytes - prevStats.bytes) * 8) / (timeDelta * 1000) : 0;

      statsRef.current.set(peerId, { bytes: totalBytes, timestamp: Date.now() });

      return {
        bitrate: Math.max(0, bitrate),
        packetLossPercent,
        avgRtt
      };
    } catch (error) {
      console.error('Failed to get peer stats:', error);
      return null;
    }
  }, []);

  const estimateBandwidth = useCallback(async () => {
    if (peers.size === 0) return null;

    let totalBitrate = 0;
    let maxPacketLoss = 0;
    let maxRtt = 0;
    let validSamples = 0;

    for (const [peerId, peer] of peers.entries()) {
      const stats = await getPeerStats(peer, peerId);
      if (stats && stats.bitrate > 0) {
        totalBitrate += stats.bitrate;
        maxPacketLoss = Math.max(maxPacketLoss, stats.packetLossPercent);
        maxRtt = Math.max(maxRtt, stats.avgRtt);
        validSamples++;
      }
    }

    if (validSamples === 0) return null;

    const avgBitrate = totalBitrate / validSamples;

    predictorRef.current.addSample(avgBitrate, maxPacketLoss, maxRtt);

    const predictedQuality = predictorRef.current.getPredictedQuality();
    setConnectionQuality(predictedQuality);

    return {
      avgBitrate,
      maxPacketLoss,
      maxRtt,
      quality: predictedQuality,
      ...predictorRef.current.getStats()
    };
  }, [peers, getPeerStats, setConnectionQuality]);

  const adaptResolution = useCallback(async () => {
    if (adaptationCooldownRef.current) return;
    if (peers.size === 0) return;

    const currentLevel = getCurrentResolutionLevel();
    currentLevelIndexRef.current = currentLevel;

    const recommendation = predictorRef.current.getRecommendedResolution(currentLevel);

    const now = Date.now();
    const timeSinceLastAdaptation = now - lastAdaptationTimeRef.current;

    let minCooldown = 10000;
    if (recommendation.confidence > 0.8) {
      minCooldown = 5000;
    } else if (recommendation.confidence > 0.6) {
      minCooldown = 8000;
    }

    if (recommendation.level === currentLevel) {
      return;
    }

    if (recommendation.level < currentLevel && timeSinceLastAdaptation < minCooldown) {
      if (recommendation.predictedQuality !== 'poor') {
        return;
      }
    }

    if (recommendation.level > currentLevel && timeSinceLastAdaptation < minCooldown * 1.5) {
      return;
    }

    adaptationCooldownRef.current = true;

    const targetResolution = RESOLUTION_LEVELS[recommendation.level];
    const currentResolutionName = RESOLUTION_LEVELS[currentLevel]?.name || '720p';

    console.log(`[Bandwidth Prediction] Adapting resolution: ${currentResolutionName} -> ${targetResolution.name}`);
    console.log(`  Predicted bandwidth: ${recommendation.predictedBandwidth.toFixed(0)} kbps`);
    console.log(`  Confidence: ${(recommendation.confidence * 100).toFixed(0)}%`);
    console.log(`  Predicted quality: ${recommendation.predictedQuality}`);
    console.log(`  Trend: ${predictorRef.current.getStats().trend.toFixed(2)}`);

    const success = await changeResolution(targetResolution.name);

    if (success) {
      currentLevelIndexRef.current = recommendation.level;
      lastAdaptationTimeRef.current = now;
    }

    setTimeout(() => {
      adaptationCooldownRef.current = false;
    }, minCooldown);
  }, [peers.size, getCurrentResolutionLevel, changeResolution]);

  useEffect(() => {
    if (peers.size === 0) {
      if (predictorRef.current) {
        predictorRef.current.reset();
      }
      statsRef.current.clear();
      return;
    }

    const monitorInterval = setInterval(async () => {
      const stats = await estimateBandwidth();
      if (stats) {
        await adaptResolution();
      }
    }, 2000);

    return () => {
      clearInterval(monitorInterval);
      if (predictorRef.current) {
        predictorRef.current.reset();
      }
      statsRef.current.clear();
    };
  }, [peers.size, estimateBandwidth, adaptResolution]);

  const getQualityColor = useCallback((quality) => {
    const colors = {
      poor: '#ef4444',
      fair: '#f59e0b',
      good: '#22c55e',
      excellent: '#10b981'
    };
    return colors[quality] || '#6b7280';
  }, []);

  const getQualityText = useCallback((quality) => {
    const texts = {
      poor: '网络较差',
      fair: '网络一般',
      good: '网络良好',
      excellent: '网络极佳'
    };
    return texts[quality] || '未知';
  }, []);

  const getPredictionStats = useCallback(() => {
    return predictorRef.current?.getStats() || null;
  }, []);

  return {
    estimateBandwidth,
    adaptResolution,
    getQualityColor,
    getQualityText,
    getPredictionStats,
    qualityHistory: predictorRef.current?.bitrateHistory || [],
    predictor: predictorRef.current
  };
};

export default useBandwidthAdaptation;
