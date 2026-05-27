package com.datasecurity.masking.proxy.server;

import com.datasecurity.masking.access.PermissionService;
import com.datasecurity.masking.access.UserContext;
import com.datasecurity.masking.access.UserContextHolder;
import com.datasecurity.masking.model.SensitiveField;
import com.datasecurity.masking.service.MetadataService;
import com.datasecurity.masking.sql.SQLParserService;
import com.datasecurity.masking.sql.SQLRewriteEngine;
import com.datasecurity.masking.strategy.MaskStrategyService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.io.*;
import java.net.Socket;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.List;

@Slf4j
@Component
public class ProxyConnectionHandler {

    @Autowired
    private SQLParserService sqlParserService;

    @Autowired
    private SQLRewriteEngine sqlRewriteEngine;

    @Autowired
    private MetadataService metadataService;

    @Autowired
    private MaskStrategyService maskStrategyService;

    @Autowired
    private PermissionService permissionService;

    private static final int MYSQL_PACKET_HEADER_SIZE = 4;
    private static final int MYSQL_COM_QUERY = 0x03;

    public void handleConnection(Socket clientSocket, String targetHost, int targetPort) throws Exception {
        try (
                Socket serverSocket = new Socket(targetHost, targetPort);
                InputStream clientIn = clientSocket.getInputStream();
                OutputStream clientOut = clientSocket.getOutputStream();
                InputStream serverIn = serverSocket.getInputStream();
                OutputStream serverOut = serverSocket.getOutputStream()
        ) {
            Thread clientToServerThread = new Thread(() -> {
                try {
                    forwardClientToServer(clientIn, serverOut);
                } catch (Exception e) {
                    log.debug("Client to server forwarding ended: {}", e.getMessage());
                }
            }, "client-to-server");

            Thread serverToClientThread = new Thread(() -> {
                try {
                    forwardServerToClient(serverIn, clientOut);
                } catch (Exception e) {
                    log.debug("Server to client forwarding ended: {}", e.getMessage());
                }
            }, "server-to-client");

            clientToServerThread.start();
            serverToClientThread.start();

            try {
                clientToServerThread.join();
                serverToClientThread.join();
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }

        } finally {
            log.debug("Connection closed");
        }
    }

    private void forwardClientToServer(InputStream clientIn, OutputStream serverOut) throws Exception {
        byte[] headerBuffer = new byte[MYSQL_PACKET_HEADER_SIZE];

        while (true) {
            int headerBytesRead = readFully(clientIn, headerBuffer);
            if (headerBytesRead < MYSQL_PACKET_HEADER_SIZE) {
                break;
            }

            int packetLength = ByteBuffer.wrap(headerBuffer, 0, 3).order(ByteOrder.LITTLE_ENDIAN).getInt() & 0xFFFFFF;
            int packetNumber = headerBuffer[3] & 0xFF;

            byte[] packetBody = new byte[packetLength];
            int bodyBytesRead = readFully(clientIn, packetBody);
            if (bodyBytesRead < packetLength) {
                break;
            }

            if (packetLength > 0 && packetBody[0] == MYSQL_COM_QUERY) {
                String sql = new String(packetBody, 1, packetLength - 1);
                log.debug("Intercepted SQL query: {}", sql);

                try {
                    String rewrittenSql = rewriteSQL(sql);
                    if (!sql.equals(rewrittenSql)) {
                        log.debug("Rewrote SQL from: {} to: {}", sql, rewrittenSql);
                        byte[] newSqlBytes = rewrittenSql.getBytes();
                        int newPacketLength = 1 + newSqlBytes.length;

                        byte[] newHeader = new byte[MYSQL_PACKET_HEADER_SIZE];
                        ByteBuffer.wrap(newHeader).order(ByteOrder.LITTLE_ENDIAN)
                                .putInt(newPacketLength);
                        newHeader[3] = headerBuffer[3];

                        serverOut.write(newHeader);
                        serverOut.write(MYSQL_COM_QUERY);
                        serverOut.write(newSqlBytes);
                        serverOut.flush();
                        continue;
                    }
                } catch (Exception e) {
                    log.warn("Failed to rewrite SQL, forwarding original: {}", e.getMessage());
                }
            }

            serverOut.write(headerBuffer);
            serverOut.write(packetBody);
            serverOut.flush();
        }
    }

    private void forwardServerToClient(InputStream serverIn, OutputStream clientOut) throws Exception {
        byte[] buffer = new byte[8192];
        int bytesRead;

        while ((bytesRead = serverIn.read(buffer)) != -1) {
            clientOut.write(buffer, 0, bytesRead);
            clientOut.flush();
        }
    }

    private int readFully(InputStream in, byte[] buffer) throws IOException {
        int totalRead = 0;
        while (totalRead < buffer.length) {
            int read = in.read(buffer, totalRead, buffer.length - totalRead);
            if (read == -1) {
                break;
            }
            totalRead += read;
        }
        return totalRead;
    }

    private String rewriteSQL(String sql) throws Exception {
        if (sqlParserService.isWriteOperation(sql)) {
            return sql;
        }

        UserContext user = UserContextHolder.get();
        if (!permissionService.needMasking(user)) {
            return sql;
        }

        List<SensitiveField> sensitiveFields = metadataService.getSensitiveFields("default");
        if (sensitiveFields == null || sensitiveFields.isEmpty()) {
            return sql;
        }

        return sqlRewriteEngine.rewriteSQL(sql, "default", true);
    }
}
