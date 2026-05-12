package com.stock.model;

public class TreeItemWrapper {

    private final Type type;
    private final WatchlistGroup group;
    private final Stock stock;

    public enum Type {
        GROUP,
        STOCK
    }

    public TreeItemWrapper(WatchlistGroup group) {
        this.type = Type.GROUP;
        this.group = group;
        this.stock = null;
    }

    public TreeItemWrapper(Stock stock) {
        this.type = Type.STOCK;
        this.group = null;
        this.stock = stock;
    }

    public Type getType() {
        return type;
    }

    public WatchlistGroup getGroup() {
        return group;
    }

    public Stock getStock() {
        return stock;
    }

    public boolean isGroup() {
        return type == Type.GROUP;
    }

    public boolean isStock() {
        return type == Type.STOCK;
    }

    @Override
    public String toString() {
        if (type == Type.GROUP) {
            return group.toString();
        } else if (stock != null) {
            return stock.getName() + " (" + stock.getCode() + ")";
        }
        return "";
    }
}
