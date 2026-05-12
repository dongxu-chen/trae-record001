package com.stock.model;

import javafx.beans.property.DoubleProperty;
import javafx.beans.property.LongProperty;
import javafx.beans.property.SimpleDoubleProperty;
import javafx.beans.property.SimpleLongProperty;
import javafx.beans.property.SimpleStringProperty;
import javafx.beans.property.StringProperty;

public class Stock {
    private final StringProperty code;
    private final StringProperty name;
    private final DoubleProperty price;
    private final DoubleProperty change;
    private final DoubleProperty changePercent;
    private final DoubleProperty open;
    private final DoubleProperty high;
    private final DoubleProperty low;
    private final DoubleProperty close;
    private final LongProperty volume;

    public Stock() {
        this.code = new SimpleStringProperty();
        this.name = new SimpleStringProperty();
        this.price = new SimpleDoubleProperty();
        this.change = new SimpleDoubleProperty();
        this.changePercent = new SimpleDoubleProperty();
        this.open = new SimpleDoubleProperty();
        this.high = new SimpleDoubleProperty();
        this.low = new SimpleDoubleProperty();
        this.close = new SimpleDoubleProperty();
        this.volume = new SimpleLongProperty();
    }

    public Stock(String code, String name, double price, double change, double changePercent) {
        this();
        setCode(code);
        setName(name);
        setPrice(price);
        setChange(change);
        setChangePercent(changePercent);
    }

    public String getCode() {
        return code.get();
    }

    public StringProperty codeProperty() {
        return code;
    }

    public void setCode(String code) {
        this.code.set(code);
    }

    public String getName() {
        return name.get();
    }

    public StringProperty nameProperty() {
        return name;
    }

    public void setName(String name) {
        this.name.set(name);
    }

    public double getPrice() {
        return price.get();
    }

    public DoubleProperty priceProperty() {
        return price;
    }

    public void setPrice(double price) {
        this.price.set(price);
    }

    public double getChange() {
        return change.get();
    }

    public DoubleProperty changeProperty() {
        return change;
    }

    public void setChange(double change) {
        this.change.set(change);
    }

    public double getChangePercent() {
        return changePercent.get();
    }

    public DoubleProperty changePercentProperty() {
        return changePercent;
    }

    public void setChangePercent(double changePercent) {
        this.changePercent.set(changePercent);
    }

    public double getOpen() {
        return open.get();
    }

    public DoubleProperty openProperty() {
        return open;
    }

    public void setOpen(double open) {
        this.open.set(open);
    }

    public double getHigh() {
        return high.get();
    }

    public DoubleProperty highProperty() {
        return high;
    }

    public void setHigh(double high) {
        this.high.set(high);
    }

    public double getLow() {
        return low.get();
    }

    public DoubleProperty lowProperty() {
        return low;
    }

    public void setLow(double low) {
        this.low.set(low);
    }

    public double getClose() {
        return close.get();
    }

    public DoubleProperty closeProperty() {
        return close;
    }

    public void setClose(double close) {
        this.close.set(close);
    }

    public long getVolume() {
        return volume.get();
    }

    public LongProperty volumeProperty() {
        return volume;
    }

    public void setVolume(long volume) {
        this.volume.set(volume);
    }
}
