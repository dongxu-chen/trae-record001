package com.datasecurity.masking.proxy.driver;

import lombok.extern.slf4j.Slf4j;

import java.sql.*;
import java.util.Properties;
import java.util.logging.Logger;

@Slf4j
public class MaskingDriver implements Driver {

    private static final String MASKING_URL_PREFIX = "jdbc:masking:";
    private static final int MAJOR_VERSION = 1;
    private static final int MINOR_VERSION = 0;

    private static MaskingDriver instance;

    static {
        try {
            instance = new MaskingDriver();
            DriverManager.registerDriver(instance);
            log.info("Masking JDBC Driver registered successfully");
        } catch (SQLException e) {
            log.error("Failed to register Masking JDBC Driver", e);
            throw new RuntimeException("Failed to register Masking JDBC Driver", e);
        }
    }

    public static synchronized MaskingDriver getInstance() {
        if (instance == null) {
            instance = new MaskingDriver();
        }
        return instance;
    }

    @Override
    public Connection connect(String url, Properties info) throws SQLException {
        if (!acceptsURL(url)) {
            return null;
        }

        log.debug("Connecting to masked database: {}", url);

        String realUrl = extractRealUrl(url);
        String databaseId = extractDatabaseId(url);

        log.debug("Real database URL: {}", realUrl);
        log.debug("Database ID for masking: {}", databaseId);

        Properties realInfo = new Properties(info);
        Driver realDriver = findRealDriver(realUrl);
        Connection realConnection = realDriver.connect(realUrl, realInfo);

        return new MaskingConnection(realConnection, databaseId);
    }

    @Override
    public boolean acceptsURL(String url) throws SQLException {
        return url != null && url.startsWith(MASKING_URL_PREFIX);
    }

    @Override
    public DriverPropertyInfo[] getPropertyInfo(String url, Properties info) throws SQLException {
        String realUrl = extractRealUrl(url);
        Driver realDriver = findRealDriver(realUrl);
        return realDriver.getPropertyInfo(realUrl, info);
    }

    @Override
    public int getMajorVersion() {
        return MAJOR_VERSION;
    }

    @Override
    public int getMinorVersion() {
        return MINOR_VERSION;
    }

    @Override
    public boolean jdbcCompliant() {
        return true;
    }

    @Override
    public Logger getParentLogger() throws SQLFeatureNotSupportedException {
        return Logger.getLogger("com.datasecurity.masking.driver");
    }

    private String extractRealUrl(String url) {
        String withoutPrefix = url.substring(MASKING_URL_PREFIX.length());

        int dbIdEndIndex = withoutPrefix.indexOf("//");
        if (dbIdEndIndex > 0) {
            String dbIdPart = withoutPrefix.substring(0, dbIdEndIndex);
            if (dbIdPart.contains("@")) {
                String afterDbId = withoutPrefix.substring(dbIdEndIndex);
                return afterDbId.replaceFirst("//", "jdbc:");
            }
        }

        return withoutPrefix.replaceFirst("mysql:", "jdbc:mysql:")
                .replaceFirst("postgresql:", "jdbc:postgresql:");
    }

    private String extractDatabaseId(String url) {
        String withoutPrefix = url.substring(MASKING_URL_PREFIX.length());
        int atIndex = withoutPrefix.indexOf("@");
        if (atIndex > 0) {
            return withoutPrefix.substring(0, atIndex);
        }
        return "default";
    }

    private Driver findRealDriver(String url) throws SQLException {
        try {
            return DriverManager.getDriver(url);
        } catch (SQLException e) {
            if (url.contains("mysql")) {
                try {
                    Class.forName("com.mysql.cj.jdbc.Driver");
                    return DriverManager.getDriver(url);
                } catch (ClassNotFoundException ex) {
                    throw new SQLException("MySQL driver not found", ex);
                }
            } else if (url.contains("postgresql")) {
                try {
                    Class.forName("org.postgresql.Driver");
                    return DriverManager.getDriver(url);
                } catch (ClassNotFoundException ex) {
                    throw new SQLException("PostgreSQL driver not found", ex);
                }
            }
            throw e;
        }
    }
}
