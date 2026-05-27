package com.datasecurity.masking.proxy.driver;

import lombok.extern.slf4j.Slf4j;

import java.sql.*;

@Slf4j
public class MaskingStatement implements Statement {

    protected final Statement realStatement;
    protected final MaskingConnection connection;
    protected ResultSet currentResultSet;

    public MaskingStatement(Statement realStatement, MaskingConnection connection) {
        this.realStatement = realStatement;
        this.connection = connection;
    }

    @Override
    public ResultSet executeQuery(String sql) throws SQLException {
        log.debug("Executing query: {}", sql);
        ResultSet realResultSet = realStatement.executeQuery(sql);
        return new MaskingResultSet(realResultSet, connection.getDatabaseId());
    }

    @Override
    public int executeUpdate(String sql) throws SQLException {
        return realStatement.executeUpdate(sql);
    }

    @Override
    public void close() throws SQLException {
        if (currentResultSet != null && !currentResultSet.isClosed()) {
            currentResultSet.close();
        }
        realStatement.close();
    }

    @Override
    public int getMaxFieldSize() throws SQLException {
        return realStatement.getMaxFieldSize();
    }

    @Override
    public void setMaxFieldSize(int max) throws SQLException {
        realStatement.setMaxFieldSize(max);
    }

    @Override
    public int getMaxRows() throws SQLException {
        return realStatement.getMaxRows();
    }

    @Override
    public void setMaxRows(int max) throws SQLException {
        realStatement.setMaxRows(max);
    }

    @Override
    public void setEscapeProcessing(boolean enable) throws SQLException {
        realStatement.setEscapeProcessing(enable);
    }

    @Override
    public int getQueryTimeout() throws SQLException {
        return realStatement.getQueryTimeout();
    }

    @Override
    public void setQueryTimeout(int seconds) throws SQLException {
        realStatement.setQueryTimeout(seconds);
    }

    @Override
    public void cancel() throws SQLException {
        realStatement.cancel();
    }

    @Override
    public SQLWarning getWarnings() throws SQLException {
        return realStatement.getWarnings();
    }

    @Override
    public void clearWarnings() throws SQLException {
        realStatement.clearWarnings();
    }

    @Override
    public void setCursorName(String name) throws SQLException {
        realStatement.setCursorName(name);
    }

    @Override
    public boolean execute(String sql) throws SQLException {
        boolean hasResultSet = realStatement.execute(sql);
        if (hasResultSet) {
            currentResultSet = new MaskingResultSet(realStatement.getResultSet(), connection.getDatabaseId());
        }
        return hasResultSet;
    }

    @Override
    public ResultSet getResultSet() throws SQLException {
        if (currentResultSet != null) {
            return currentResultSet;
        }
        ResultSet realRs = realStatement.getResultSet();
        if (realRs != null) {
            return new MaskingResultSet(realRs, connection.getDatabaseId());
        }
        return null;
    }

    @Override
    public int getUpdateCount() throws SQLException {
        return realStatement.getUpdateCount();
    }

    @Override
    public boolean getMoreResults() throws SQLException {
        boolean hasMore = realStatement.getMoreResults();
        if (hasMore) {
            currentResultSet = new MaskingResultSet(realStatement.getResultSet(), connection.getDatabaseId());
        }
        return hasMore;
    }

    @Override
    public void setFetchDirection(int direction) throws SQLException {
        realStatement.setFetchDirection(direction);
    }

    @Override
    public int getFetchDirection() throws SQLException {
        return realStatement.getFetchDirection();
    }

    @Override
    public void setFetchSize(int rows) throws SQLException {
        realStatement.setFetchSize(rows);
    }

    @Override
    public int getFetchSize() throws SQLException {
        return realStatement.getFetchSize();
    }

    @Override
    public int getResultSetConcurrency() throws SQLException {
        return realStatement.getResultSetConcurrency();
    }

    @Override
    public int getResultSetType() throws SQLException {
        return realStatement.getResultSetType();
    }

    @Override
    public void addBatch(String sql) throws SQLException {
        realStatement.addBatch(sql);
    }

    @Override
    public void clearBatch() throws SQLException {
        realStatement.clearBatch();
    }

    @Override
    public int[] executeBatch() throws SQLException {
        return realStatement.executeBatch();
    }

    @Override
    public Connection getConnection() throws SQLException {
        return connection;
    }

    @Override
    public boolean getMoreResults(int current) throws SQLException {
        boolean hasMore = realStatement.getMoreResults(current);
        if (hasMore) {
            currentResultSet = new MaskingResultSet(realStatement.getResultSet(), connection.getDatabaseId());
        }
        return hasMore;
    }

    @Override
    public ResultSet getGeneratedKeys() throws SQLException {
        return realStatement.getGeneratedKeys();
    }

    @Override
    public int executeUpdate(String sql, int autoGeneratedKeys) throws SQLException {
        return realStatement.executeUpdate(sql, autoGeneratedKeys);
    }

    @Override
    public int executeUpdate(String sql, int[] columnIndexes) throws SQLException {
        return realStatement.executeUpdate(sql, columnIndexes);
    }

    @Override
    public int executeUpdate(String sql, String[] columnNames) throws SQLException {
        return realStatement.executeUpdate(sql, columnNames);
    }

    @Override
    public boolean execute(String sql, int autoGeneratedKeys) throws SQLException {
        boolean hasResultSet = realStatement.execute(sql, autoGeneratedKeys);
        if (hasResultSet) {
            currentResultSet = new MaskingResultSet(realStatement.getResultSet(), connection.getDatabaseId());
        }
        return hasResultSet;
    }

    @Override
    public boolean execute(String sql, int[] columnIndexes) throws SQLException {
        boolean hasResultSet = realStatement.execute(sql, columnIndexes);
        if (hasResultSet) {
            currentResultSet = new MaskingResultSet(realStatement.getResultSet(), connection.getDatabaseId());
        }
        return hasResultSet;
    }

    @Override
    public boolean execute(String sql, String[] columnNames) throws SQLException {
        boolean hasResultSet = realStatement.execute(sql, columnNames);
        if (hasResultSet) {
            currentResultSet = new MaskingResultSet(realStatement.getResultSet(), connection.getDatabaseId());
        }
        return hasResultSet;
    }

    @Override
    public int getResultSetHoldability() throws SQLException {
        return realStatement.getResultSetHoldability();
    }

    @Override
    public boolean isClosed() throws SQLException {
        return realStatement.isClosed();
    }

    @Override
    public void setPoolable(boolean poolable) throws SQLException {
        realStatement.setPoolable(poolable);
    }

    @Override
    public boolean isPoolable() throws SQLException {
        return realStatement.isPoolable();
    }

    @Override
    public void closeOnCompletion() throws SQLException {
        realStatement.closeOnCompletion();
    }

    @Override
    public boolean isCloseOnCompletion() throws SQLException {
        return realStatement.isCloseOnCompletion();
    }

    @Override
    public <T> T unwrap(Class<T> iface) throws SQLException {
        if (iface.isAssignableFrom(this.getClass())) {
            return (T) this;
        }
        return realStatement.unwrap(iface);
    }

    @Override
    public boolean isWrapperFor(Class<?> iface) throws SQLException {
        return iface.isAssignableFrom(this.getClass()) || realStatement.isWrapperFor(iface);
    }
}
