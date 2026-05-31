package com.drill.platform.engine;

import com.drill.platform.model.TrafficProfile;

public class TrafficCurveGenerator {

    private final TrafficProfile profile;

    public TrafficCurveGenerator(TrafficProfile profile) {
        this.profile = profile;
    }

    public int getQpsAtSecond(int second) {
        int rampUp = profile.getRampUpSeconds();
        int sustain = profile.getSustainSeconds();
        int rampDown = profile.getRampDownSeconds();
        int baseQps = profile.getBaseQps();
        int peakQps = profile.getPeakQps();

        if (second < 0) return baseQps;

        if (second < rampUp) {
            return generateRampUpQps(second, rampUp, baseQps, peakQps);
        } else if (second < rampUp + sustain) {
            return generateSustainQps(second - rampUp, sustain, peakQps);
        } else if (second < rampUp + sustain + rampDown) {
            int rampDownSecond = second - rampUp - sustain;
            return generateRampDownQps(rampDownSecond, rampDown, baseQps, peakQps);
        }

        return baseQps;
    }

    private int generateRampUpQps(int second, int rampUpSeconds, int baseQps, int peakQps) {
        double progress = (double) second / rampUpSeconds;
        double ratio = 0;

        switch (profile.getPattern()) {
            case LINEAR_RAMP:
                ratio = progress;
                break;
            case EXPONENTIAL_RAMP:
                ratio = Math.expm1(progress * 5) / Math.expm1(5);
                break;
            case LOGARITHMIC_RAMP:
                ratio = Math.log10(1 + progress * 9);
                break;
            case SIGMOID_RAMP:
                ratio = 1.0 / (1.0 + Math.exp(-10 * (progress - 0.5)));
                break;
            case SPIKE:
                return second >= rampUpSeconds - 1 ? peakQps : baseQps;
            case WAVE:
                double wave = Math.sin(Math.PI * progress);
                return baseQps + (int) ((peakQps - baseQps) * wave);
            case STEP:
                int steps = 5;
                int stepSize = rampUpSeconds / steps;
                int step = second / stepSize;
                return baseQps + (peakQps - baseQps) * step / steps;
            case DOUBLE_STEP:
                if (progress < 0.5) {
                    ratio = 0.5 * (progress * 2);
                } else {
                    ratio = 0.5 + 0.5 * ((progress - 0.5) * 2);
                }
                break;
            case GRADUAL_STEP:
                int gradualSteps = 10;
                int gradualStepSize = rampUpSeconds / gradualSteps;
                int gradualStep = second / gradualStepSize;
                ratio = (double) gradualStep / gradualSteps;
                break;
            case CONSTANT:
            default:
                return peakQps;
        }
        return baseQps + (int) ((peakQps - baseQps) * ratio);
    }

    private int generateSustainQps(int second, int sustainSeconds, int peakQps) {
        switch (profile.getPattern()) {
            case WAVE:
                double wave = Math.sin(2 * Math.PI * second / sustainSeconds * 3);
                return (int) (peakQps * (0.7 + 0.3 * wave));
            case STEP:
                return peakQps + (int) (peakQps * 0.1 * Math.sin(second));
            default:
                return peakQps;
        }
    }

    private int generateRampDownQps(int second, int rampDownSeconds, int baseQps, int peakQps) {
        double ratio = 1.0 - (double) second / rampDownSeconds;
        return baseQps + (int) ((peakQps - baseQps) * ratio);
    }
}
