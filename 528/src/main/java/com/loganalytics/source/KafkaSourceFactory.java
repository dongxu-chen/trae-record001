package com.loganalytics.source;

import com.loganalytics.config.FlinkConfig;
import com.loganalytics.model.NginxLogEvent;
import com.loganalytics.parser.NginxLogParser;
import org.apache.flink.api.common.eventtime.WatermarkStrategy;
import org.apache.flink.api.common.serialization.DeserializationSchema;
import org.apache.flink.api.common.typeinfo.TypeInformation;
import org.apache.flink.connector.kafka.source.KafkaSource;
import org.apache.flink.connector.kafka.source.enumerator.initializer.OffsetsInitializer;
import org.apache.flink.streaming.api.datastream.DataStreamSource;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.kafka.clients.consumer.OffsetResetStrategy;

import java.io.IOException;
import java.nio.charset.StandardCharsets;

public class KafkaSourceFactory {

    public static DataStreamSource<NginxLogEvent> createNginxLogSource(
            StreamExecutionEnvironment env,
            FlinkConfig config) {

        KafkaSource<NginxLogEvent> source = KafkaSource.<NginxLogEvent>builder()
                .setBootstrapServers(config.getKafkaBrokers())
                .setTopics(config.getKafkaTopic())
                .setGroupId(config.getKafkaGroupId())
                .setStartingOffsets(OffsetsInitializer.committedOffsets(OffsetResetStrategy.LATEST))
                .setValueOnlyDeserializer(new NginxLogDeserializationSchema())
                .build();

        return env.fromSource(source, WatermarkStrategy.forMonotonousTimestamps(), "nginx-logs-kafka-source");
    }

    public static class NginxLogDeserializationSchema implements DeserializationSchema<NginxLogEvent> {
        @Override
        public NginxLogEvent deserialize(byte[] message) throws IOException {
            if (message == null) {
                return null;
            }
            String logLine = new String(message, StandardCharsets.UTF_8);
            return NginxLogParser.parse(logLine);
        }

        @Override
        public boolean isEndOfStream(NginxLogEvent nextElement) {
            return false;
        }

        @Override
        public TypeInformation<NginxLogEvent> getProducedType() {
            return TypeInformation.of(NginxLogEvent.class);
        }
    }
}
