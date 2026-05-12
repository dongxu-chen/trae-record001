package com.stock.model;

import javafx.beans.property.*;

public class AppSettings {

    private final IntegerProperty refreshIntervalSeconds;
    private final BooleanProperty autoRefreshOnStartup;
    private final BooleanProperty enableWebSocket;
    private final IntegerProperty defaultKlineDays;
    private final StringProperty theme;
    private final StringProperty lastExportPath;
    private final BooleanProperty showPriceAlertDialog;

    public AppSettings() {
        this.refreshIntervalSeconds = new SimpleIntegerProperty(10);
        this.autoRefreshOnStartup = new SimpleBooleanProperty(true);
        this.enableWebSocket = new SimpleBooleanProperty(false);
        this.defaultKlineDays = new SimpleIntegerProperty(60);
        this.theme = new SimpleStringProperty("默认");
        this.lastExportPath = new SimpleStringProperty(System.getProperty("user.home"));
        this.showPriceAlertDialog = new SimpleBooleanProperty(true);
    }

    public int getRefreshIntervalSeconds() {
        return refreshIntervalSeconds.get();
    }

    public IntegerProperty refreshIntervalSecondsProperty() {
        return refreshIntervalSeconds;
    }

    public void setRefreshIntervalSeconds(int refreshIntervalSeconds) {
        this.refreshIntervalSeconds.set(refreshIntervalSeconds);
    }

    public boolean isAutoRefreshOnStartup() {
        return autoRefreshOnStartup.get();
    }

    public BooleanProperty autoRefreshOnStartupProperty() {
        return autoRefreshOnStartup;
    }

    public void setAutoRefreshOnStartup(boolean autoRefreshOnStartup) {
        this.autoRefreshOnStartup.set(autoRefreshOnStartup);
    }

    public boolean isEnableWebSocket() {
        return enableWebSocket.get();
    }

    public BooleanProperty enableWebSocketProperty() {
        return enableWebSocket;
    }

    public void setEnableWebSocket(boolean enableWebSocket) {
        this.enableWebSocket.set(enableWebSocket);
    }

    public int getDefaultKlineDays() {
        return defaultKlineDays.get();
    }

    public IntegerProperty defaultKlineDaysProperty() {
        return defaultKlineDays;
    }

    public void setDefaultKlineDays(int defaultKlineDays) {
        this.defaultKlineDays.set(defaultKlineDays);
    }

    public String getTheme() {
        return theme.get();
    }

    public StringProperty themeProperty() {
        return theme;
    }

    public void setTheme(String theme) {
        this.theme.set(theme);
    }

    public String getLastExportPath() {
        return lastExportPath.get();
    }

    public StringProperty lastExportPathProperty() {
        return lastExportPath;
    }

    public void setLastExportPath(String lastExportPath) {
        this.lastExportPath.set(lastExportPath);
    }

    public boolean isShowPriceAlertDialog() {
        return showPriceAlertDialog.get();
    }

    public BooleanProperty showPriceAlertDialogProperty() {
        return showPriceAlertDialog;
    }

    public void setShowPriceAlertDialog(boolean showPriceAlertDialog) {
        this.showPriceAlertDialog.set(showPriceAlertDialog);
    }
}
