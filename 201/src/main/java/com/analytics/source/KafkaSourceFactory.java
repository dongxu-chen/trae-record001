package com.analytics.source;

import com.analytics.model.UserBehaviorEvent;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.flink.api.common.serialization.DeserializationSchema;
import org.apache.flink.api.common.typeinfo.TypeInformation;
import org.apache.flink.connector.kafka.source.KafkaSource;
import org.apache.flink.connector.kafka.source.enumerator.initializer.OffsetsInitializer;

import java.io.IOException;

public class KafkaSourceFactory {

    private static final ObjectMapper objectMapper = new ObjectMapper();

    public static KafkaSource<UserBehaviorEvent> createKafkaSource(
            String bootstrapServers,
            String topic,
            String groupId) {

        return KafkaSource.<UserBehaviorEvent>builder()
                .setBootstrapServers(bootstrapServers)
                .setTopics(topic)
                .setGroupId(groupId)
                .setStartingOffsets(OffsetsInitializer.latest())
                .setValueOnlyDeserializer(new UserBehaviorEventDeserializationSchema())
                .build();
    }

    public static class UserBehaviorEventDeserializationSchema 
            implements DeserializationSchema<UserBehaviorEvent> {

        @Override
        public UserBehaviorEvent deserialize(byte[] message) throws IOException {
            if (message == null || message.length == 0) {
                return null;
            }
            try {
                return objectMapper.readValue(message, UserBehaviorEvent.class);
            } catch (Exception e) {
                return null;
            }
        }

        @Override
        public boolean isEndOfStream(UserBehaviorEvent nextElement) {
            return false;
        }

        @Override
        public TypeInformation<UserBehaviorEvent> getProducedType() {
            return TypeInformation.of(UserBehaviorEvent.class);
        }
    }
}
