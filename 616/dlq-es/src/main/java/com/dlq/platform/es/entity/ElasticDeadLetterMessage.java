package com.dlq.platform.es.entity;

import co.elastic.clients.elasticsearch._types.mapping.DateProperty;
import co.elastic.clients.elasticsearch._types.mapping.IntegerNumberProperty;
import co.elastic.clients.elasticsearch._types.mapping.KeywordProperty;
import co.elastic.clients.elasticsearch._types.mapping.ObjectProperty;
import co.elastic.clients.elasticsearch._types.mapping.Property;
import co.elastic.clients.elasticsearch._types.mapping.TextProperty;
import com.dlq.platform.common.entity.DeadLetterMessage;
import com.dlq.platform.es.constants.EsIndexConstants;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.EqualsAndHashCode;
import lombok.NoArgsConstructor;
import lombok.experimental.SuperBuilder;

import java.util.HashMap;
import java.util.Map;

@Data
@SuperBuilder
@NoArgsConstructor
@AllArgsConstructor
@EqualsAndHashCode(callSuper = true)
public class ElasticDeadLetterMessage extends DeadLetterMessage {

    private String indexName;

    public static Map<String, Property> getMappings() {
        Map<String, Property> properties = new HashMap<>();

        properties.put(EsIndexConstants.FIELD_ID, Property.of(p -> p.keyword(KeywordProperty.of(k -> k))));
        properties.put(EsIndexConstants.FIELD_MQ_TYPE, Property.of(p -> p.keyword(KeywordProperty.of(k -> k))));
        properties.put(EsIndexConstants.FIELD_TOPIC, Property.of(p -> p.keyword(KeywordProperty.of(k -> k))));
        properties.put(EsIndexConstants.FIELD_QUEUE_NAME, Property.of(p -> p.keyword(KeywordProperty.of(k -> k))));
        properties.put(EsIndexConstants.FIELD_MESSAGE_ID, Property.of(p -> p.keyword(KeywordProperty.of(k -> k))));

        properties.put(EsIndexConstants.FIELD_MESSAGE_BODY, Property.of(p -> p.text(TextProperty.of(t -> t
                .analyzer(EsIndexConstants.ANALYZER_IK_MAX_WORD)
                .searchAnalyzer(EsIndexConstants.ANALYZER_IK_SMART)
                .fields("keyword", Property.of(f -> f.keyword(KeywordProperty.of(k -> k.ignoreAbove(256))))
        )))));

        properties.put(EsIndexConstants.FIELD_HEADERS, Property.of(p -> p.object(ObjectProperty.of(o -> o.dynamic(true)))));

        properties.put(EsIndexConstants.FIELD_DEAD_REASON, Property.of(p -> p.text(TextProperty.of(t -> t
                .analyzer(EsIndexConstants.ANALYZER_IK_MAX_WORD)
                .searchAnalyzer(EsIndexConstants.ANALYZER_IK_SMART)
                .fields("keyword", Property.of(f -> f.keyword(KeywordProperty.of(k -> k.ignoreAbove(256))))
        )))));

        properties.put(EsIndexConstants.FIELD_DEAD_REASON_TYPE, Property.of(p -> p.keyword(KeywordProperty.of(k -> k))));
        properties.put(EsIndexConstants.FIELD_STACK_TRACE, Property.of(p -> p.text(TextProperty.of(t -> t.analyzer("standard")))));
        properties.put(EsIndexConstants.FIELD_ORIGINAL_TOPIC, Property.of(p -> p.keyword(KeywordProperty.of(k -> k))));
        properties.put(EsIndexConstants.FIELD_ORIGINAL_QUEUE, Property.of(p -> p.keyword(KeywordProperty.of(k -> k))));
        properties.put(EsIndexConstants.FIELD_RETRY_COUNT, Property.of(p -> p.integer(IntegerNumberProperty.of(i -> i))));
        properties.put(EsIndexConstants.FIELD_PROCESS_STATUS, Property.of(p -> p.keyword(KeywordProperty.of(k -> k))));

        properties.put(EsIndexConstants.FIELD_CREATE_TIME, Property.of(p -> p.date(DateProperty.of(d -> d.format("yyyy-MM-dd HH:mm:ss||epoch_millis")))));
        properties.put(EsIndexConstants.FIELD_UPDATE_TIME, Property.of(p -> p.date(DateProperty.of(d -> d.format("yyyy-MM-dd HH:mm:ss||epoch_millis")))));

        return properties;
    }

    public static Map<String, Object> getSettings() {
        Map<String, Object> settings = new HashMap<>();
        settings.put("number_of_shards", 3);
        settings.put("number_of_replicas", 1);
        settings.put("refresh_interval", "5s");

        Map<String, Object> analysis = new HashMap<>();
        Map<String, Object> analyzer = new HashMap<>();

        Map<String, Object> ikMaxWord = new HashMap<>();
        ikMaxWord.put("type", "ik_max_word");
        analyzer.put("ik_max_word", ikMaxWord);

        Map<String, Object> ikSmart = new HashMap<>();
        ikSmart.put("type", "ik_smart");
        analyzer.put("ik_smart", ikSmart);

        analysis.put("analyzer", analyzer);
        settings.put("analysis", analysis);

        return settings;
    }
}
