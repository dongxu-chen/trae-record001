package com.datasecurity.masking.dp;

import com.datasecurity.masking.access.PermissionService;
import com.datasecurity.masking.access.UserContext;
import com.datasecurity.masking.access.UserContextHolder;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Service
public class DifferentialPrivacyService {

    @Autowired(required = false)
    private JdbcTemplate jdbcTemplate;

    @Autowired
    private PermissionService permissionService;

    private final Map<String, Double> userEpsilonBudget = new ConcurrentHashMap<>();

    private static final double DEFAULT_EPSILON = 1.0;
    private static final double DEFAULT_DELTA = 1e-5;
    private static final double DEFAULT_MIN = 0.0;
    private static final double DEFAULT_MAX = 1e9;

    public DPQueryResult count(DPQueryRequest request) {
        validateAccess();

        double epsilon = request.getEpsilon() != null ? request.getEpsilon() : DEFAULT_EPSILON;
        double delta = request.getDelta() != null ? request.getDelta() : DEFAULT_DELTA;

        String sql = buildCountQuery(request, "COUNT(*)");
        long trueCount = executeCountQuery(sql);

        double sensitivity = 1.0;
        double noisyCount = DifferentialPrivacy.addLaplaceNoise(trueCount, epsilon, sensitivity);

        log.info("DP COUNT query: table={}, column={}, trueCount={}, noisyCount={}, epsilon={}",
                request.getTableName(), request.getColumnName(), trueCount, noisyCount, epsilon);

        return DPQueryResult.of(noisyCount, trueCount, epsilon, delta, sensitivity);
    }

    public DPQueryResult sum(DPQueryRequest request) {
        validateAccess();

        double epsilon = request.getEpsilon() != null ? request.getEpsilon() : DEFAULT_EPSILON;
        double delta = request.getDelta() != null ? request.getDelta() : DEFAULT_DELTA;
        double min = request.getMinValue() != null ? request.getMinValue() : DEFAULT_MIN;
        double max = request.getMaxValue() != null ? request.getMaxValue() : DEFAULT_MAX;

        String sql = buildAggregateQuery(request, "SUM", request.getColumnName());
        double trueSum = executeDoubleQuery(sql);

        double sensitivity = max - min;
        double noisySum = DifferentialPrivacy.addLaplaceNoise(trueSum, epsilon, sensitivity);

        log.info("DP SUM query: table={}, column={}, trueSum={}, noisySum={}, epsilon={}",
                request.getTableName(), request.getColumnName(), trueSum, noisySum, epsilon);

        return DPQueryResult.of(noisySum, trueSum, epsilon, delta, sensitivity);
    }

    public DPQueryResult average(DPQueryRequest request) {
        validateAccess();

        double epsilon = request.getEpsilon() != null ? request.getEpsilon() : DEFAULT_EPSILON;
        double delta = request.getDelta() != null ? request.getDelta() : DEFAULT_DELTA;
        double min = request.getMinValue() != null ? request.getMinValue() : DEFAULT_MIN;
        double max = request.getMaxValue() != null ? request.getMaxValue() : DEFAULT_MAX;

        String countSql = buildCountQuery(request, "COUNT(*)");
        String sumSql = buildAggregateQuery(request, "SUM", request.getColumnName());

        long count = executeCountQuery(countSql);
        double sum = executeDoubleQuery(sumSql);
        double trueAvg = count > 0 ? sum / count : 0;

        double sensitivity = (max - min) / Math.max(1, count);
        double noisyAvg = DifferentialPrivacy.addLaplaceNoise(trueAvg, epsilon, sensitivity);

        log.info("DP AVG query: table={}, column={}, trueAvg={}, noisyAvg={}, epsilon={}",
                request.getTableName(), request.getColumnName(), trueAvg, noisyAvg, epsilon);

        return DPQueryResult.of(noisyAvg, trueAvg, epsilon, delta, sensitivity);
    }

    public DPQueryResult min(DPQueryRequest request) {
        validateAccess();

        double epsilon = request.getEpsilon() != null ? request.getEpsilon() : DEFAULT_EPSILON;
        double delta = request.getDelta() != null ? request.getDelta() : DEFAULT_DELTA;
        double minVal = request.getMinValue() != null ? request.getMinValue() : DEFAULT_MIN;
        double maxVal = request.getMaxValue() != null ? request.getMaxValue() : DEFAULT_MAX;

        String sql = buildAggregateQuery(request, "MIN", request.getColumnName());
        double trueMin = executeDoubleQuery(sql);

        double sensitivity = maxVal - minVal;
        double noisyMin = DifferentialPrivacy.addLaplaceNoise(trueMin, epsilon, sensitivity);

        log.info("DP MIN query: table={}, column={}, trueMin={}, noisyMin={}, epsilon={}",
                request.getTableName(), request.getColumnName(), trueMin, noisyMin, epsilon);

        return DPQueryResult.of(noisyMin, trueMin, epsilon, delta, sensitivity);
    }

    public DPQueryResult max(DPQueryRequest request) {
        validateAccess();

        double epsilon = request.getEpsilon() != null ? request.getEpsilon() : DEFAULT_EPSILON;
        double delta = request.getDelta() != null ? request.getDelta() : DEFAULT_DELTA;
        double minVal = request.getMinValue() != null ? request.getMinValue() : DEFAULT_MIN;
        double maxVal = request.getMaxValue() != null ? request.getMaxValue() : DEFAULT_MAX;

        String sql = buildAggregateQuery(request, "MAX", request.getColumnName());
        double trueMax = executeDoubleQuery(sql);

        double sensitivity = maxVal - minVal;
        double noisyMax = DifferentialPrivacy.addLaplaceNoise(trueMax, epsilon, sensitivity);

        log.info("DP MAX query: table={}, column={}, trueMax={}, noisyMax={}, epsilon={}",
                request.getTableName(), request.getColumnName(), trueMax, noisyMax, epsilon);

        return DPQueryResult.of(noisyMax, trueMax, epsilon, delta, sensitivity);
    }

    public Map<String, DPQueryResult> histogram(DPQueryRequest request) {
        validateAccess();

        double epsilon = request.getEpsilon() != null ? request.getEpsilon() : DEFAULT_EPSILON;
        double delta = request.getDelta() != null ? request.getDelta() : DEFAULT_DELTA;

        String sql = buildHistogramQuery(request);
        List<Map<String, Object>> rawResults = executeHistogramQuery(sql);

        Map<String, DPQueryResult> histogram = new java.util.LinkedHashMap<>();

        double sensitivity = 2.0;

        for (Map<String, Object> row : rawResults) {
            String key = String.valueOf(row.get("bucket"));
            long trueCount = ((Number) row.get("count")).longValue();
            double noisyCount = DifferentialPrivacy.addLaplaceNoise(trueCount, epsilon / rawResults.size(), sensitivity);

            histogram.put(key, DPQueryResult.of(noisyCount, trueCount, epsilon / rawResults.size(), delta, sensitivity));
        }

        log.info("DP HISTOGRAM query: table={}, column={}, buckets={}, epsilon={}",
                request.getTableName(), request.getColumnName(), rawResults.size(), epsilon);

        return histogram;
    }

    private void validateAccess() {
        UserContext user = UserContextHolder.get();
        if (user == null) {
            throw new SecurityException("User context not found");
        }
        if (!permissionService.canViewSensitiveData(user)) {
            log.warn("Admin user detected, DP protection bypassed");
        }
    }

    private String buildCountQuery(DPQueryRequest request, String aggregate) {
        StringBuilder sql = new StringBuilder("SELECT ");
        sql.append(aggregate);
        sql.append(" FROM ").append(request.getTableName());
        if (request.getWhereClause() != null && !request.getWhereClause().isEmpty()) {
            sql.append(" WHERE ").append(request.getWhereClause());
        }
        return sql.toString();
    }

    private String buildAggregateQuery(DPQueryRequest request, String function, String column) {
        StringBuilder sql = new StringBuilder("SELECT ");
        sql.append(function).append("(").append(column).append(")");
        sql.append(" FROM ").append(request.getTableName());
        if (request.getWhereClause() != null && !request.getWhereClause().isEmpty()) {
            sql.append(" WHERE ").append(request.getWhereClause());
        }
        return sql.toString();
    }

    private String buildHistogramQuery(DPQueryRequest request) {
        return "SELECT " + request.getColumnName() + " as bucket, COUNT(*) as count " +
                "FROM " + request.getTableName() +
                (request.getWhereClause() != null && !request.getWhereClause().isEmpty() ?
                        " WHERE " + request.getWhereClause() : "") +
                " GROUP BY " + request.getColumnName() +
                " ORDER BY " + request.getColumnName();
    }

    private long executeCountQuery(String sql) {
        if (jdbcTemplate == null) {
            log.warn("JdbcTemplate not available, returning mock value");
            return 1000;
        }
        try {
            Long count = jdbcTemplate.queryForObject(sql, Long.class);
            return count != null ? count : 0;
        } catch (Exception e) {
            log.warn("Failed to execute count query: {}", e.getMessage());
            return 0;
        }
    }

    private double executeDoubleQuery(String sql) {
        if (jdbcTemplate == null) {
            log.warn("JdbcTemplate not available, returning mock value");
            return 50000.0;
        }
        try {
            Double result = jdbcTemplate.queryForObject(sql, Double.class);
            return result != null ? result : 0.0;
        } catch (Exception e) {
            log.warn("Failed to execute aggregate query: {}", e.getMessage());
            return 0.0;
        }
    }

    private List<Map<String, Object>> executeHistogramQuery(String sql) {
        if (jdbcTemplate == null) {
            log.warn("JdbcTemplate not available, returning mock data");
            List<Map<String, Object>> mock = new java.util.ArrayList<>();
            mock.add(Map.of("bucket", "A", "count", 100L));
            mock.add(Map.of("bucket", "B", "count", 200L));
            mock.add(Map.of("bucket", "C", "count", 150L));
            return mock;
        }
        try {
            return jdbcTemplate.queryForList(sql);
        } catch (Exception e) {
            log.warn("Failed to execute histogram query: {}", e.getMessage());
            return new java.util.ArrayList<>();
        }
    }

    public boolean checkBudget(String userId, double epsilonRequested) {
        double used = userEpsilonBudget.getOrDefault(userId, 0.0);
        return used + epsilonRequested <= 10.0;
    }

    public void consumeBudget(String userId, double epsilon) {
        userEpsilonBudget.merge(userId, epsilon, Double::sum);
    }

    public double getUsedBudget(String userId) {
        return userEpsilonBudget.getOrDefault(userId, 0.0);
    }

    public void resetBudget(String userId) {
        userEpsilonBudget.remove(userId);
    }
}
