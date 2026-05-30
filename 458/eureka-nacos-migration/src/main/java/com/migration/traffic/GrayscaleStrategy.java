package com.migration.traffic;

import lombok.Data;

@Data
public class GrayscaleStrategy {

    private String serviceId;
    private double nacosTrafficRatio;

    public GrayscaleStrategy(String serviceId) {
        this.serviceId = serviceId;
        this.nacosTrafficRatio = 0.0;
    }

    public GrayscaleStrategy(String serviceId, double nacosTrafficRatio) {
        this.serviceId = serviceId;
        setNacosTrafficRatio(nacosTrafficRatio);
    }

    public void setNacosTrafficRatio(double ratio) {
        if (ratio < 0.0 || ratio > 1.0) {
            throw new IllegalArgumentException("Traffic ratio must be between 0.0 and 1.0");
        }
        this.nacosTrafficRatio = ratio;
    }

    public boolean isAllEureka() {
        return nacosTrafficRatio <= 0.0;
    }

    public boolean isAllNacos() {
        return nacosTrafficRatio >= 1.0;
    }

    public int getNacosPercentage() {
        return (int) Math.round(nacosTrafficRatio * 100);
    }

    public void setNacosPercentage(int percentage) {
        if (percentage < 0 || percentage > 100) {
            throw new IllegalArgumentException("Percentage must be between 0 and 100");
        }
        this.nacosTrafficRatio = percentage / 100.0;
    }

    public boolean shouldRouteToNacos() {
        if (isAllEureka()) return false;
        if (isAllNacos()) return true;
        return Math.random() < nacosTrafficRatio;
    }

    public String getStatusDescription() {
        if (isAllEureka()) {
            return "All traffic to Eureka (0% Nacos)";
        } else if (isAllNacos()) {
            return "All traffic to Nacos (100% Nacos)";
        } else {
            return String.format("Grayscale: %d%% traffic to Nacos, %d%% to Eureka",
                    getNacosPercentage(), 100 - getNacosPercentage());
        }
    }
}
