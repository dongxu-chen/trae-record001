package com.stock.model;

import javafx.beans.property.SimpleStringProperty;
import javafx.beans.property.StringProperty;
import javafx.collections.FXCollections;
import javafx.collections.ObservableList;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

public class WatchlistGroup {

    private final StringProperty id;
    private final StringProperty name;
    private final ObservableList<String> stockCodes;

    public WatchlistGroup(String name) {
        this(UUID.randomUUID().toString(), name, new ArrayList<>());
    }

    public WatchlistGroup(String id, String name, List<String> stockCodes) {
        this.id = new SimpleStringProperty(id);
        this.name = new SimpleStringProperty(name);
        this.stockCodes = FXCollections.observableArrayList(stockCodes);
    }

    public String getId() {
        return id.get();
    }

    public StringProperty idProperty() {
        return id;
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

    public ObservableList<String> getStockCodes() {
        return stockCodes;
    }

    public void addStock(String code) {
        if (!stockCodes.contains(code)) {
            stockCodes.add(code);
        }
    }

    public void removeStock(String code) {
        stockCodes.remove(code);
    }

    public boolean containsStock(String code) {
        return stockCodes.contains(code);
    }

    public int getStockCount() {
        return stockCodes.size();
    }

    @Override
    public String toString() {
        return name.get() + " (" + stockCodes.size() + ")";
    }
}
