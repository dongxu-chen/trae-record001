package com.datacheck.datasource;

import co.elastic.clients.elasticsearch.ElasticsearchClient;
import co.elastic.clients.elasticsearch._types.Time;
import co.elastic.clients.elasticsearch.core.GetResponse;
import co.elastic.clients.elasticsearch.core.SearchRequest;
import co.elastic.clients.elasticsearch.core.SearchResponse;
import co.elastic.clients.elasticsearch.core.search.Hit;
import co.elastic.clients.elasticsearch.indices.GetMappingResponse;
import com.alibaba.fastjson2.JSON;
import com.datacheck.model.CheckTask;
import com.datacheck.model.DataRecord;
import com.datacheck.model.enums.DataSourceType;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.stereotype.Component;

import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Component
public class ElasticsearchDataSourceAdapter implements DataSourceAdapter {

    private final ElasticsearchClient sourceEsClient;
    private final ElasticsearchClient targetEsClient;

    @Autowired
    public ElasticsearchDataSourceAdapter(
            @Qualifier("sourceElasticsearchClient") ElasticsearchClient sourceEsClient,
            @Qualifier("targetElasticsearchClient") ElasticsearchClient targetEsClient) {
        this.sourceEsClient = sourceEsClient;
        this.targetEsClient = targetEsClient;
    }

    @Override
    public DataSourceType getType() {
        return DataSourceType.ELASTICSEARCH;
    }

    @Override
    public Iterator<DataRecord> iterateSource(CheckTask task) {
        return new EsRecordIterator(sourceEsClient, task);
    }

    @Override
    public Iterator<DataRecord> iterateTarget(CheckTask task) {
        return new EsRecordIterator(targetEsClient, task);
    }

    @Override
    public DataRecord getSourceRecord(String key, CheckTask task) {
        return getRecord(sourceEsClient, key, task);
    }

    @Override
    public DataRecord getTargetRecord(String key, CheckTask task) {
        return getRecord(targetEsClient, key, task);
    }

    @Override
    public long getSourceCount(CheckTask task) {
        return getCount(sourceEsClient, task);
    }

    @Override
    public long getTargetCount(CheckTask task) {
        return getCount(targetEsClient, task);
    }

    @Override
    public boolean insertTarget(DataRecord record, CheckTask task) {
        return writeDocument(targetEsClient, record, task);
    }

    @Override
    public boolean updateTarget(DataRecord record, CheckTask task) {
        return writeDocument(targetEsClient, record, task);
    }

    @Override
    public boolean deleteTarget(String key, CheckTask task) {
        try {
            targetEsClient.delete(d -> d.index(task.getTableName()).id(key));
            log.info("Successfully deleted ES document, id: {}, index: {}", key, task.getTableName());
            return true;
        } catch (Exception e) {
            log.error("Failed to delete ES document, id: {}, index: {}", key, task.getTableName(), e);
            return false;
        }
    }

    @Override
    public List<String> getPrimaryKeys(String tableName) {
        return Collections.singletonList("id");
    }

    @Override
    public List<String> getColumns(String tableName) {
        try {
            GetMappingResponse response = sourceEsClient.indices().getMapping(m -> m.index(tableName));
            Map<String, Object> properties = (Map<String, Object>) response.result().get(tableName)
                    .mappings().properties();
            return new ArrayList<>(properties.keySet());
        } catch (Exception e) {
            log.error("Failed to get ES mapping for index: {}", tableName, e);
            return Collections.emptyList();
        }
    }

    @SuppressWarnings("unchecked")
    private DataRecord getRecord(ElasticsearchClient esClient, String key, CheckTask task) {
        try {
            GetResponse<Map> response = esClient.get(g -> g
                            .index(task.getTableName())
                            .id(key),
                    Map.class);
            if (!response.found()) {
                return null;
            }
            Map<String, Object> data = new LinkedHashMap<>();
            data.put("id", response.id());
            if (response.source() != null) {
                data.putAll(response.source());
            }
            return DataRecord.builder()
                    .key(response.id())
                    .data(data)
                    .sourceType(DataSourceType.ELASTICSEARCH)
                    .timestamp(System.currentTimeMillis())
                    .tableName(task.getTableName())
                    .build();
        } catch (Exception e) {
            log.error("Failed to get ES document, id: {}, index: {}", key, task.getTableName(), e);
            return null;
        }
    }

    private long getCount(ElasticsearchClient esClient, CheckTask task) {
        try {
            co.elastic.clients.elasticsearch.core.CountRequest.Builder builder =
                    new co.elastic.clients.elasticsearch.core.CountRequest.Builder()
                            .index(task.getTableName());
            if (task.getWhereCondition() != null && !task.getWhereCondition().isEmpty()) {
                builder.query(q -> q.queryString(qs -> qs.query(task.getWhereCondition())));
            }
            return esClient.count(builder.build()).count();
        } catch (Exception e) {
            log.error("Failed to get ES count for index: {}", task.getTableName(), e);
            return 0;
        }
    }

    @SuppressWarnings("unchecked")
    private boolean writeDocument(ElasticsearchClient esClient, DataRecord record, CheckTask task) {
        try {
            Map<String, Object> source = new LinkedHashMap<>(record.getData());
            source.remove("id");
            esClient.index(i -> i
                    .index(task.getTableName())
                    .id(record.getKey())
                    .document(source));
            log.info("Successfully wrote ES document, id: {}, index: {}", record.getKey(), task.getTableName());
            return true;
        } catch (Exception e) {
            log.error("Failed to write ES document, id: {}, index: {}", record.getKey(), task.getTableName(), e);
            return false;
        }
    }

    private class EsRecordIterator implements Iterator<DataRecord> {
        private final ElasticsearchClient esClient;
        private final CheckTask task;
        private final int batchSize;
        private String scrollId;
        private List<DataRecord> currentBatch;
        private int currentIndex = 0;
        private boolean hasMore = true;

        public EsRecordIterator(ElasticsearchClient esClient, CheckTask task) {
            this.esClient = esClient;
            this.task = task;
            this.batchSize = task.getBatchSize() != null ? task.getBatchSize() : 1000;
            initScroll();
        }

        @SuppressWarnings("unchecked")
        private void initScroll() {
            try {
                SearchRequest.Builder builder = new SearchRequest.Builder()
                        .index(task.getTableName())
                        .size(batchSize)
                        .scroll(Time.of(t -> t.time("1m")));

                if (task.getCompareFields() != null && !task.getCompareFields().isEmpty()) {
                    List<String> fields = new ArrayList<>(task.getCompareFields());
                    if (!fields.contains("id")) {
                        fields.add(0, "id");
                    }
                    builder.source(s -> s.filter(f -> f.includes(fields)));
                }

                if (task.getExcludeFields() != null && !task.getExcludeFields().isEmpty()) {
                    builder.source(s -> s.filter(f -> f.excludes(task.getExcludeFields())));
                }

                if (task.getWhereCondition() != null && !task.getWhereCondition().isEmpty()) {
                    builder.query(q -> q.queryString(qs -> qs.query(task.getWhereCondition())));
                }

                builder.sort(s -> s.field(f -> f.field("_doc")));

                SearchResponse<Map> response = esClient.search(builder.build(), Map.class);
                scrollId = response.scrollId();
                processResponse(response);
            } catch (Exception e) {
                log.error("Failed to initialize ES scroll for index: {}", task.getTableName(), e);
                hasMore = false;
                currentBatch = Collections.emptyList();
            }
        }

        @SuppressWarnings("unchecked")
        private void fetchNextBatch() {
            try {
                if (scrollId == null) {
                    hasMore = false;
                    currentBatch = Collections.emptyList();
                    return;
                }
                SearchResponse<Map> response = esClient.scroll(s -> s
                        .scrollId(scrollId)
                        .scroll(Time.of(t -> t.time("1m"))), Map.class);
                processResponse(response);
            } catch (Exception e) {
                log.error("Failed to fetch ES batch", e);
                hasMore = false;
                currentBatch = Collections.emptyList();
                clearScroll();
            }
        }

        @SuppressWarnings("unchecked")
        private void processResponse(SearchResponse<Map> response) {
            List<Hit<Map>> hits = response.hits().hits();
            if (hits.isEmpty()) {
                hasMore = false;
                currentBatch = Collections.emptyList();
                clearScroll();
                return;
            }
            currentBatch = new ArrayList<>();
            for (Hit<Map> hit : hits) {
                Map<String, Object> data = new LinkedHashMap<>();
                data.put("id", hit.id());
                if (hit.source() != null) {
                    data.putAll(hit.source());
                }
                currentBatch.add(DataRecord.builder()
                        .key(hit.id())
                        .data(data)
                        .sourceType(DataSourceType.ELASTICSEARCH)
                        .timestamp(System.currentTimeMillis())
                        .tableName(task.getTableName())
                        .build());
            }
            currentIndex = 0;
        }

        private void clearScroll() {
            if (scrollId != null) {
                try {
                    esClient.clearScroll(c -> c.scrollId(scrollId));
                } catch (Exception e) {
                    log.warn("Failed to clear ES scroll: {}", scrollId, e);
                }
                scrollId = null;
            }
        }

        @Override
        public boolean hasNext() {
            if (currentIndex < currentBatch.size()) {
                return true;
            }
            if (hasMore) {
                fetchNextBatch();
                return currentIndex < currentBatch.size();
            }
            return false;
        }

        @Override
        public DataRecord next() {
            if (!hasNext()) {
                throw new NoSuchElementException();
            }
            return currentBatch.get(currentIndex++);
        }
    }
}
