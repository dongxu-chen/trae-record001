package com.analytics.source;

import com.analytics.model.PipelineDynamicConfig;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.flink.api.common.serialization.DeserializationSchema;
import org.apache.flink.api.common.typeinfo.TypeInformation;
import org.apache.flink.connector.kafka.source.KafkaSource;
import org.apache.flink.connector.kafka.source.enumerator.initializer.OffsetsInitializer;

import java.io.IOException;

public class DynamicConfigSourceFactory {

    private static final ObjectMapper objectMapper = new ObjectMapper();

    public static KafkaSource<PipelineDynamicConfig> createConfigSource(
            String bootstrapServers,
            String topic,
            String groupId) {

        return KafkaSource.<PipelineDynamicConfig>builder()
                .setBootstrapServers(bootstrapServers)
                .setTopics(topic)
                .setGroupId(groupId + "_config")
                .setStartingOffsets(OffsetsInitializer.latest())
                .setValueOnlyDeserializer(new DynamicConfigDeserializationSchema())
                .build();
    }

    public static class DynamicConfigDeserializationSchema 
            implements DeserializationSchema<PipelineDynamicConfig> {

        @Override
        public PipelineDynamicConfig deserialize(byte[] message) throws IOException {
            if (message == null || message.length == 0) {
                return null;
            }
            try {
                return objectMapper.readValue(message, PipelineDynamicConfig.class);
            } catch (Exception e) {
                return null;
            }
        }

        @Override
        public boolean isEndOfStream(PipelineDynamicConfig nextElement) {
            return false;
        }

        @Override
        public TypeInformation<PipelineDynamicConfig> getProducedType() {
            return TypeInformation.of(PipelineDynamicConfig.class);
        }
    }
}
