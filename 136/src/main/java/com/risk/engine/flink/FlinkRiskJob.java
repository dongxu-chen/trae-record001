package com.risk.engine.flink;

import com.alibaba.fastjson.JSON;
import com.risk.engine.dto.DecisionRequest;
import com.risk.engine.dto.DecisionResponse;
import com.risk.engine.rules.DynamicRuleEngine;
import lombok.extern.slf4j.Slf4j;
import org.apache.flink.api.common.functions.RichMapFunction;
import org.apache.flink.api.common.serialization.SimpleStringSchema;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.streaming.connectors.kafka.FlinkKafkaConsumer;
import org.apache.flink.streaming.connectors.kafka.FlinkKafkaProducer;
import org.jeasy.rules.api.Facts;
import org.springframework.stereotype.Component;

import java.util.*;

@Slf4j
@Component
public class FlinkRiskJob {

    public void runJob(String kafkaBootstrapServers, String inputTopic, String outputTopic) throws Exception {
        StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();
        
        Properties consumerProps = new Properties();
        consumerProps.setProperty("bootstrap.servers", kafkaBootstrapServers);
        consumerProps.setProperty("group.id", "risk-engine-group");
        
        FlinkKafkaConsumer<String> consumer = new FlinkKafkaConsumer<>(
            inputTopic,
            new SimpleStringSchema(),
            consumerProps
        );
        
        DataStream<String> inputStream = env.addSource(consumer);
        
        DataStream<String> resultStream = inputStream
            .map(new RiskDecisionFunction())
            .map(JSON::toJSONString);
        
        Properties producerProps = new Properties();
        producerProps.setProperty("bootstrap.servers", kafkaBootstrapServers);
        
        FlinkKafkaProducer<String> producer = new FlinkKafkaProducer<>(
            outputTopic,
            new SimpleStringSchema(),
            producerProps
        );
        
        resultStream.addSink(producer);
        
        env.execute("Flink-Risk-Engine-Job");
    }

    public static class RiskDecisionFunction extends RichMapFunction<String, DecisionResponse> {
        
        private transient DynamicRuleEngine ruleEngine;
        
        @Override
        public void open(Configuration parameters) throws Exception {
            ruleEngine = new DynamicRuleEngine();
            ruleEngine.loadAllRules();
        }
        
        @Override
        public DecisionResponse map(String value) throws Exception {
            try {
                DecisionRequest request = JSON.parseObject(value, DecisionRequest.class);
                String scene = request.getScene() != null ? request.getScene() : "DEFAULT";
                
                Facts facts = new Facts();
                facts.put("requestId", request.getRequestId());
                facts.put("scene", scene);
                facts.put("data", request.getData());
                facts.put("decision", "PASS");
                facts.put("score", 0);
                facts.put("hitRules", new ArrayList<>());
                
                ruleEngine.fireRules(scene, facts);
                
                DecisionResponse response = new DecisionResponse();
                response.setRequestId(request.getRequestId());
                response.setDecision((String) facts.get("decision"));
                response.setScore((Integer) facts.get("score"));
                response.setHitRules((List<String>) facts.get("hitRules"));
                
                return response;
            } catch (Exception e) {
                log.error("Flink流式决策失败", e);
                DecisionResponse errorResponse = new DecisionResponse();
                errorResponse.setDecision("ERROR");
                errorResponse.setErrorMsg(e.getMessage());
                return errorResponse;
            }
        }
        
        @Override
        public void close() throws Exception {
        }
    }
}
