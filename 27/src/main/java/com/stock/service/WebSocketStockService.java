package com.stock.service;

import com.stock.model.Stock;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.Proxy;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.WebSocket;
import java.nio.ByteBuffer;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.function.Consumer;

public class WebSocketStockService {

    private static final String SINA_WS_URL = "wss://hq.sinajs.cn/list=";

    private final ExecutorService executor = Executors.newFixedThreadPool(1, r -> {
        Thread t = new Thread(r, "stock-websocket");
        t.setDaemon(true);
        return t;
    });

    private final Map<String, Consumer<Stock>> listeners = new ConcurrentHashMap<>();
    private final Set<String> subscribedCodes = ConcurrentHashMap.newKeySet();
    private final AtomicBoolean connected = new AtomicBoolean(false);
    private final AtomicBoolean connecting = new AtomicBoolean(false);

    private WebSocket webSocket;
    private HttpClient httpClient;
    private ScheduledExecutorService heartbeatScheduler;
    private ScheduledFuture<?> heartbeatFuture;
    private ScheduledExecutorService reconnectScheduler;
    private ScheduledFuture<?> reconnectFuture;

    private final long RECONNECT_DELAY = 5000;
    private final long HEARTBEAT_INTERVAL = 30000;
    private final Random random = new Random();

    public interface WebSocketListener {
        void onPriceUpdate(Stock stock);
        void onConnected();
        void onDisconnected();
        void onError(String message);
    }

    private final List<WebSocketListener> wsListeners = new CopyOnWriteArrayList<>();

    public void addListener(String code, Consumer<Stock> listener) {
        listeners.put(code, listener);
        subscribe(code);
    }

    public void removeListener(String code) {
        listeners.remove(code);
        unsubscribe(code);
    }

    public void addWsListener(WebSocketListener listener) {
        wsListeners.add(listener);
    }

    public void removeWsListener(WebSocketListener listener) {
        wsListeners.remove(listener);
    }

    public boolean isConnected() {
        return connected.get();
    }

    public void connect() {
        if (connecting.compareAndSet(false, true)) {
            executor.submit(this::doConnect);
        }
    }

    private void doConnect() {
        try {
            httpClient = HttpClient.newBuilder()
                    .connectTimeout(Duration.ofSeconds(10))
                    .proxy(Proxy.NO_PROXY)
                    .build();

            String codes = String.join(",", subscribedCodes);
            if (codes.isEmpty()) {
                codes = "sh600519";
            }

            String wsUrl = "wss://ws.sinajs.cn/ws";

            webSocket = httpClient.newWebSocketBuilder()
                    .connectTimeout(Duration.ofSeconds(15))
                    .buildAsync(URI.create(wsUrl), new WebSocket.Listener() {
                        @Override
                        public void onOpen(WebSocket ws) {
                            System.out.println("WebSocket 已连接");
                            connected.set(true);
                            connecting.set(false);
                            notifyConnected();
                            startHeartbeat();
                            cancelReconnect();

                            for (String code : subscribedCodes) {
                                sendSubscribe(code);
                            }
                        }

                        @Override
                        public CompletionStage<?> onText(WebSocket ws, CharSequence data, boolean last) {
                            handleMessage(data.toString());
                            return WebSocket.Listener.super.onText(ws, data, last);
                        }

                        @Override
                        public CompletionStage<?> onBinary(WebSocket ws, ByteBuffer data, boolean last) {
                            System.out.println("收到二进制消息");
                            return WebSocket.Listener.super.onBinary(ws, data, last);
                        }

                        @Override
                        public CompletionStage<?> onClose(WebSocket ws, int statusCode, String reason) {
                            System.out.println("WebSocket 关闭: " + statusCode + " - " + reason);
                            handleDisconnect();
                            return WebSocket.Listener.super.onClose(ws, statusCode, reason);
                        }

                        @Override
                        public void onError(WebSocket ws, Throwable error) {
                            System.err.println("WebSocket 错误: " + error.getMessage());
                            notifyError(error.getMessage());
                            handleDisconnect();
                        }
                    })
                    .join();

        } catch (Exception e) {
            System.err.println("WebSocket 连接失败: " + e.getMessage());
            connecting.set(false);
            notifyError(e.getMessage());
            scheduleReconnect();
        }
    }

    private void handleMessage(String message) {
        if (message == null || message.isEmpty()) {
            return;
        }

        if (message.equals("ping") || message.equals("pong")) {
            return;
        }

        simulateMockUpdate();
    }

    private void simulateMockUpdate() {
        for (Map.Entry<String, Consumer<Stock>> entry : listeners.entrySet()) {
            String code = entry.getKey();
            Consumer<Stock> consumer = entry.getValue();

            double basePrice = 50 + random.nextDouble() * 100;
            double change = (random.nextDouble() - 0.5) * 5;
            double price = basePrice + change;

            Stock stock = new Stock();
            stock.setCode(code);
            stock.setName("股票" + code);
            stock.setPrice(price);
            stock.setChange(change);
            stock.setChangePercent((change / basePrice) * 100);
            stock.setOpen(basePrice);
            stock.setHigh(price + random.nextDouble() * 2);
            stock.setLow(price - random.nextDouble() * 2);
            stock.setClose(basePrice);
            stock.setVolume((long) (random.nextDouble() * 10000000));

            try {
                consumer.accept(stock);
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
    }

    private void sendSubscribe(String code) {
        if (webSocket != null && connected.get()) {
            String marketPrefix = code.startsWith("6") ? "sh" : "sz";
            String message = "sub=" + marketPrefix + code;
            webSocket.sendText(message, true);
        }
    }

    private void sendUnsubscribe(String code) {
        if (webSocket != null && connected.get()) {
            String marketPrefix = code.startsWith("6") ? "sh" : "sz";
            String message = "unsub=" + marketPrefix + code;
            webSocket.sendText(message, true);
        }
    }

    public void subscribe(String code) {
        if (subscribedCodes.add(code)) {
            if (connected.get()) {
                sendSubscribe(code);
            } else if (!connecting.get()) {
                connect();
            }
        }
    }

    public void unsubscribe(String code) {
        subscribedCodes.remove(code);
        sendUnsubscribe(code);
    }

    private void startHeartbeat() {
        if (heartbeatScheduler == null) {
            heartbeatScheduler = Executors.newSingleThreadScheduledExecutor(r -> {
                Thread t = new Thread(r, "ws-heartbeat");
                t.setDaemon(true);
                return t;
            });
        }

        cancelHeartbeat();

        heartbeatFuture = heartbeatScheduler.scheduleAtFixedRate(() -> {
            if (webSocket != null && connected.get()) {
                try {
                    webSocket.sendPing(ByteBuffer.wrap("hb".getBytes()));
                } catch (Exception e) {
                    System.err.println("心跳发送失败: " + e.getMessage());
                }
            }
        }, HEARTBEAT_INTERVAL, HEARTBEAT_INTERVAL, TimeUnit.MILLISECONDS);
    }

    private void cancelHeartbeat() {
        if (heartbeatFuture != null) {
            heartbeatFuture.cancel(false);
            heartbeatFuture = null;
        }
    }

    private void scheduleReconnect() {
        if (reconnectScheduler == null) {
            reconnectScheduler = Executors.newSingleThreadScheduledExecutor(r -> {
                Thread t = new Thread(r, "ws-reconnect");
                t.setDaemon(true);
                return t;
            });
        }

        cancelReconnect();

        reconnectFuture = reconnectScheduler.schedule(() -> {
            if (!connected.get() && !connecting.get()) {
                System.out.println("尝试重连 WebSocket...");
                connect();
            }
        }, RECONNECT_DELAY, TimeUnit.MILLISECONDS);
    }

    private void cancelReconnect() {
        if (reconnectFuture != null) {
            reconnectFuture.cancel(false);
            reconnectFuture = null;
        }
    }

    private void handleDisconnect() {
        connected.set(false);
        connecting.set(false);
        notifyDisconnected();
        cancelHeartbeat();
        scheduleReconnect();
    }

    private void notifyConnected() {
        for (WebSocketListener listener : wsListeners) {
            try {
                listener.onConnected();
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
    }

    private void notifyDisconnected() {
        for (WebSocketListener listener : wsListeners) {
            try {
                listener.onDisconnected();
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
    }

    private void notifyError(String message) {
        for (WebSocketListener listener : wsListeners) {
            try {
                listener.onError(message);
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
    }

    public void disconnect() {
        cancelHeartbeat();
        cancelReconnect();

        if (webSocket != null) {
            try {
                webSocket.sendClose(WebSocket.NORMAL_CLOSURE, "用户断开");
            } catch (Exception e) {
                e.printStackTrace();
            }
        }

        connected.set(false);
        connecting.set(false);

        if (heartbeatScheduler != null) {
            heartbeatScheduler.shutdownNow();
            heartbeatScheduler = null;
        }
        if (reconnectScheduler != null) {
            reconnectScheduler.shutdownNow();
            reconnectScheduler = null;
        }
        executor.shutdownNow();
    }
}
