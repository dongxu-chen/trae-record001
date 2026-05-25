package com.tracking.storage.dao;

import com.alibaba.fastjson2.JSON;
import com.tracking.common.constant.TrackingConstants;
import com.tracking.common.model.SankeyPath;
import com.tracking.common.model.UserPathQuery;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
import redis.clients.jedis.Jedis;
import redis.clients.jedis.JedisPool;

import javax.sql.DataSource;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.*;

@Repository
public class UserPathDao {

    private static final Logger LOG = LoggerFactory.getLogger(UserPathDao.class);

    private final JdbcTemplate jdbcTemplate;
    private final JedisPool jedisPool;

    public UserPathDao(DataSource dataSource, JedisPool jedisPool) {
        this.jdbcTemplate = new JdbcTemplate(dataSource);
        this.jedisPool = jedisPool;
    }

    public SankeyPath getUserPathSankey(UserPathQuery query) {
        int maxPathLength = query.getMaxPathLength() != null ? 
            query.getMaxPathLength() : TrackingConstants.PATH_MAX_LENGTH;
        int topN = query.getTopN() != null ? query.getTopN() : TrackingConstants.PATH_TOP_N;

        String cacheKey = buildCacheKey(query);
        SankeyPath cached = getFromCache(cacheKey);
        if (cached != null) {
            return cached;
        }

        List<Map<String, Object>> rawPaths = getRawPaths(query, maxPathLength, topN);
        SankeyPath sankeyPath = convertToSankey(rawPaths);

        saveToCache(cacheKey, sankeyPath);
        return sankeyPath;
    }

    public List<Map<String, Object>> getTopPaths(UserPathQuery query) {
        int maxPathLength = query.getMaxPathLength() != null ? 
            query.getMaxPathLength() : TrackingConstants.PATH_MAX_LENGTH;
        int topN = query.getTopN() != null ? query.getTopN() : TrackingConstants.PATH_TOP_N;

        return getRawPaths(query, maxPathLength, topN);
    }

    private List<Map<String, Object>> getRawPaths(UserPathQuery query, int maxPathLength, int topN) {
        StringBuilder sql = new StringBuilder();
        List<Object> params = new ArrayList<>();

        sql.append("SELECT " +
            "  session_id, " +
            "  user_id, " +
            "  groupArray(event_type) as path_events, " +
            "  groupArray(properties->'url') as path_urls, " +
            "  count(*) as event_count " +
            "FROM ( " +
            "  SELECT " +
            "    session_id, " +
            "    user_id, " +
            "    event_type, " +
            "    properties, " +
            "    timestamp, " +
            "    row_number() OVER (PARTITION BY session_id ORDER BY timestamp) as rn " +
            "  FROM " + TrackingConstants.CLICKHOUSE_TABLE_EVENTS + " " +
            "  WHERE timestamp >= ? AND timestamp <= ? ");

        params.add(query.getStartTime());
        params.add(query.getEndTime());

        if (query.getPlatform() != null) {
            sql.append("AND platform = ? ");
            params.add(query.getPlatform());
        }
        if (query.getAppId() != null) {
            sql.append("AND app_id = ? ");
            params.add(query.getAppId());
        }
        if (query.getUserId() != null) {
            sql.append("AND user_id = ? ");
            params.add(query.getUserId());
        }
        if (query.getSessionId() != null) {
            sql.append("AND session_id = ? ");
            params.add(query.getSessionId());
        }

        sql.append("  ORDER BY session_id, timestamp " +
                   ") " +
                   "WHERE rn <= ? ");
        params.add(maxPathLength);

        sql.append("GROUP BY session_id, user_id ");

        if (query.getStartEvent() != null) {
            sql.append("HAVING path_events[1] = ? ");
            params.add(query.getStartEvent());
        }

        sql.append("ORDER BY event_count DESC LIMIT ?");
        params.add(topN);

        try {
            return jdbcTemplate.queryForList(sql.toString(), params.toArray());
        } catch (Exception e) {
            LOG.warn("Failed to get user paths from ClickHouse", e);
            return new ArrayList<>();
        }
    }

    private SankeyPath convertToSankey(List<Map<String, Object>> rawPaths) {
        Map<String, Long> nodeMap = new LinkedHashMap<>();
        Map<String, Long> linkMap = new LinkedHashMap<>();

        for (Map<String, Object> row : rawPaths) {
            Object eventsObj = row.get("path_events");
            if (eventsObj == null) continue;

            String[] events = parseClickHouseArray(eventsObj.toString());
            String[] urls = null;

            Object urlsObj = row.get("path_urls");
            if (urlsObj != null) {
                urls = parseClickHouseArray(urlsObj.toString());
            }

            for (int i = 0; i < events.length; i++) {
                String nodeName = getNodeName(events[i], urls, i);
                nodeMap.merge(nodeName, 1L, Long::sum);

                if (i < events.length - 1) {
                    String sourceNode = getNodeName(events[i], urls, i);
                    String targetNode = getNodeName(events[i + 1], urls, i + 1);
                    String linkKey = sourceNode + " -> " + targetNode;
                    linkMap.merge(linkKey, 1L, Long::sum);
                }
            }
        }

        List<SankeyPath.SankeyNode> nodes = new ArrayList<>();
        Map<String, Integer> nodeIndexMap = new HashMap<>();
        int index = 0;
        for (Map.Entry<String, Long> entry : nodeMap.entrySet()) {
            String category = determineCategory(entry.getKey());
            nodes.add(SankeyPath.SankeyNode.builder()
                .id("node_" + index)
                .name(entry.getKey())
                .category(category)
                .value(entry.getValue())
                .build());
            nodeIndexMap.put(entry.getKey(), index);
            index++;
        }

        List<SankeyPath.SankeyLink> links = new ArrayList<>();
        for (Map.Entry<String, Long> entry : linkMap.entrySet()) {
            String[] parts = entry.getKey().split(" -> ");
            if (parts.length == 2 && nodeIndexMap.containsKey(parts[0]) && nodeIndexMap.containsKey(parts[1])) {
                links.add(SankeyPath.SankeyLink.builder()
                    .source("node_" + nodeIndexMap.get(parts[0]))
                    .target("node_" + nodeIndexMap.get(parts[1]))
                    .value(entry.getValue())
                    .sourceName(parts[0])
                    .targetName(parts[1])
                    .build());
            }
        }

        links.sort((a, b) -> Long.compare(b.getValue(), a.getValue()));
        if (links.size() > 50) {
            links = links.subList(0, 50);
        }

        return SankeyPath.builder()
                .nodes(nodes)
                .links(links)
                .build();
    }

    private String getNodeName(String event, String[] urls, int index) {
        if (urls != null && index < urls.length && !urls[index].isEmpty() && !urls[index].equals("")) {
            String url = urls[index];
            if (url.length() > 30) {
                url = url.substring(0, 27) + "...";
            }
            return event + " (" + url + ")";
        }
        return event;
    }

    private String determineCategory(String nodeName) {
        if (nodeName.contains(TrackingConstants.PATH_NODE_PAGE_VIEW)) {
            return "page_view";
        } else if (nodeName.contains(TrackingConstants.PATH_NODE_CLICK)) {
            return "click";
        } else if (nodeName.contains(TrackingConstants.PATH_NODE_CONVERSION) ||
                   nodeName.contains("purchase") || nodeName.contains("signup") ||
                   nodeName.contains("register")) {
            return "conversion";
        }
        return "other";
    }

    private String[] parseClickHouseArray(String arrayStr) {
        if (arrayStr == null || arrayStr.isEmpty()) {
            return new String[0];
        }
        arrayStr = arrayStr.trim();
        if (arrayStr.startsWith("[") && arrayStr.endsWith("]")) {
            arrayStr = arrayStr.substring(1, arrayStr.length() - 1);
        }
        if (arrayStr.isEmpty()) {
            return new String[0];
        }
        return arrayStr.split(",");
    }

    private String buildCacheKey(UserPathQuery query) {
        StringBuilder sb = new StringBuilder("path:sankey:");
        sb.append(query.getStartTime()).append(":").append(query.getEndTime()).append(":");
        if (query.getPlatform() != null) sb.append(query.getPlatform()).append(":");
        if (query.getAppId() != null) sb.append(query.getAppId()).append(":");
        if (query.getStartEvent() != null) sb.append(query.getStartEvent()).append(":");
        if (query.getMaxPathLength() != null) sb.append(query.getMaxPathLength()).append(":");
        if (query.getTopN() != null) sb.append(query.getTopN());
        return sb.toString();
    }

    private SankeyPath getFromCache(String key) {
        try (Jedis jedis = jedisPool.getResource()) {
            String json = jedis.get(key);
            if (json != null) {
                return JSON.parseObject(json, SankeyPath.class);
            }
        } catch (Exception e) {
            LOG.warn("Failed to get sankey path from cache", e);
        }
        return null;
    }

    private void saveToCache(String key, SankeyPath path) {
        try (Jedis jedis = jedisPool.getResource()) {
            jedis.setex(key, 3600, JSON.toJSONString(path));
        } catch (Exception e) {
            LOG.warn("Failed to save sankey path to cache", e);
        }
    }

    private int mapRowForPath(ResultSet rs, int rowNum) throws SQLException {
        return rs.getInt("cnt");
    }
}
