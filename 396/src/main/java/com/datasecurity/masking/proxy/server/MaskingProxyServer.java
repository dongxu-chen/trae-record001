package com.datasecurity.masking.proxy.server;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.annotation.PostConstruct;
import javax.annotation.PreDestroy;
import java.io.IOException;
import java.net.ServerSocket;
import java.net.Socket;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;

@Slf4j
@Component
public class MaskingProxyServer {

    @Value("${data-masking.proxy.port:3307}")
    private int proxyPort;

    @Value("${data-masking.proxy.target.host:localhost}")
    private String targetHost;

    @Value("${data-masking.proxy.target.port:3306}")
    private int targetPort;

    @Value("${data-masking.proxy.enabled:false}")
    private boolean proxyEnabled;

    @Value("${data-masking.proxy.thread-pool-size:100}")
    private int threadPoolSize;

    @Autowired
    private ProxyConnectionHandler connectionHandler;

    private ServerSocket serverSocket;
    private ExecutorService threadPool;
    private AtomicBoolean running = new AtomicBoolean(false);
    private Thread acceptThread;

    @PostConstruct
    public void start() {
        if (!proxyEnabled) {
            log.info("Masking proxy server is disabled");
            return;
        }

        log.info("Starting masking proxy server on port {}, forwarding to {}:{}",
                proxyPort, targetHost, targetPort);

        try {
            serverSocket = new ServerSocket(proxyPort);
            threadPool = Executors.newFixedThreadPool(threadPoolSize);
            running.set(true);

            acceptThread = new Thread(this::acceptConnections, "proxy-acceptor");
            acceptThread.start();

            log.info("Masking proxy server started successfully");
        } catch (IOException e) {
            log.error("Failed to start masking proxy server", e);
            throw new RuntimeException("Failed to start proxy server", e);
        }
    }

    private void acceptConnections() {
        while (running.get() && !serverSocket.isClosed()) {
            try {
                Socket clientSocket = serverSocket.accept();
                log.info("New client connection from: {}", clientSocket.getRemoteSocketAddress());

                threadPool.submit(() -> {
                    try {
                        connectionHandler.handleConnection(clientSocket, targetHost, targetPort);
                    } catch (Exception e) {
                        log.error("Error handling connection", e);
                    }
                });
            } catch (IOException e) {
                if (running.get()) {
                    log.error("Error accepting connection", e);
                }
            }
        }
    }

    @PreDestroy
    public void stop() {
        log.info("Stopping masking proxy server...");
        running.set(false);

        if (serverSocket != null) {
            try {
                serverSocket.close();
            } catch (IOException e) {
                log.warn("Error closing server socket", e);
            }
        }

        if (threadPool != null) {
            threadPool.shutdownNow();
        }

        if (acceptThread != null) {
            try {
                acceptThread.join(5000);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }

        log.info("Masking proxy server stopped");
    }
}
