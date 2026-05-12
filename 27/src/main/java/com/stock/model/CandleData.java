package com.stock.model;

public class CandleData {
    private final double open;
    private final double close;
    private final double high;
    private final double low;
    private final long volume;
    private final String date;

    public CandleData(double open, double close, double high, double low, long volume, String date) {
        this.open = open;
        this.close = close;
        this.high = high;
        this.low = low;
        this.volume = volume;
        this.date = date;
    }

    public double getOpen() {
        return open;
    }

    public double getClose() {
        return close;
    }

    public double getHigh() {
        return high;
    }

    public double getLow() {
        return low;
    }

    public long getVolume() {
        return volume;
    }

    public String getDate() {
        return date;
    }

    public boolean isUp() {
        return close >= open;
    }
}
