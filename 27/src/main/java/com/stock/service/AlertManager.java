package com.stock.service;

import com.stock.model.Stock;
import javafx.application.Platform;
import javafx.scene.control.Alert;
import javafx.scene.control.Alert.AlertType;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicBoolean;

public class AlertManager {

    private final Map<String, PriceAlert> alerts = new ConcurrentHashMap<>();
    private final List<AlertListener> listeners = new ArrayList<>();
    private final Set<String> triggeredCodes = ConcurrentHashMap.newKeySet();
    private final AtomicBoolean showingDialog = new AtomicBoolean(false);
    private final Queue<PendingAlert> pendingQueue = new ArrayDeque<>();

    public synchronized void addPriceAlert(String code, double targetPrice, boolean above) {
        alerts.put(code, new PriceAlert(code, targetPrice, above));
        triggeredCodes.remove(code);
    }

    public synchronized void removePriceAlert(String code) {
        alerts.remove(code);
    }

    public boolean hasAlert(String code) {
        return alerts.containsKey(code);
    }

    public void checkAlerts(Stock stock) {
        if (stock == null || stock.getCode() == null) {
            return;
        }

        String code = stock.getCode();

        if (triggeredCodes.contains(code)) {
            return;
        }

        PriceAlert alert = alerts.get(code);
        if (alert == null) {
            return;
        }

        boolean triggered = false;
        String message = "";

        if (alert.isAbove() && stock.getPrice() >= alert.getTargetPrice()) {
            triggered = true;
            message = String.format("股票 %s (%s) 价格已达到 %.2f，超过预警价格 %.2f",
                    stock.getName(), stock.getCode(), stock.getPrice(), alert.getTargetPrice());
        } else if (!alert.isAbove() && stock.getPrice() <= alert.getTargetPrice()) {
            triggered = true;
            message = String.format("股票 %s (%s) 价格已下跌至 %.2f，低于预警价格 %.2f",
                    stock.getName(), stock.getCode(), stock.getPrice(), alert.getTargetPrice());
        }

        if (triggered) {
            alerts.remove(code);
            triggeredCodes.add(code);
            synchronized (pendingQueue) {
                pendingQueue.offer(new PendingAlert(stock, message));
            }
            Platform.runLater(this::showNextAlert);
        }
    }

    private void showNextAlert() {
        PendingAlert pending;
        synchronized (pendingQueue) {
            if (pendingQueue.isEmpty()) {
                return;
            }
            if (showingDialog.getAndSet(true)) {
                return;
            }
            pending = pendingQueue.poll();
        }

        if (pending == null) {
            showingDialog.set(false);
            return;
        }

        notifyListeners(pending.stock, pending.message);
        showAlert(pending.message, () -> {
            showingDialog.set(false);
            if (!pendingQueue.isEmpty()) {
                Platform.runLater(this::showNextAlert);
            }
        });
    }

    private void showAlert(String message, Runnable onClose) {
        Alert alert = new Alert(AlertType.INFORMATION);
        alert.setTitle("股票价格提醒");
        alert.setHeaderText("价格预警触发");
        alert.setContentText(message);
        alert.setOnHidden(event -> {
            if (onClose != null) {
                onClose.run();
            }
        });
        alert.show();
    }

    public synchronized void addAlertListener(AlertListener listener) {
        listeners.add(listener);
    }

    public synchronized void removeAlertListener(AlertListener listener) {
        listeners.remove(listener);
    }

    private void notifyListeners(Stock stock, String message) {
        List<AlertListener> snapshot;
        synchronized (this) {
            snapshot = new ArrayList<>(listeners);
        }
        for (AlertListener listener : snapshot) {
            try {
                listener.onAlertTriggered(stock, message);
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
    }

    public interface AlertListener {
        void onAlertTriggered(Stock stock, String message);
    }

    public static class PriceAlert {
        private final String code;
        private final double targetPrice;
        private final boolean above;

        public PriceAlert(String code, double targetPrice, boolean above) {
            this.code = code;
            this.targetPrice = targetPrice;
            this.above = above;
        }

        public String getCode() {
            return code;
        }

        public double getTargetPrice() {
            return targetPrice;
        }

        public boolean isAbove() {
            return above;
        }
    }

    private static class PendingAlert {
        final Stock stock;
        final String message;

        PendingAlert(Stock stock, String message) {
            this.stock = stock;
            this.message = message;
        }
    }
}
