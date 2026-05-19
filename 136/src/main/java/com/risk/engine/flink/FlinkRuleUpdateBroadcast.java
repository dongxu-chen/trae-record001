package com.risk.engine.flink;

import com.alibaba.fastjson.JSON;
import com.risk.engine.entity.EasyRule;
import com.risk.engine.rules.DynamicRuleEngine;
import lombok.extern.slf4j.Slf4j;
import org.apache.flink.api.common.state.BroadcastState;
import org.apache.flink.api.common.state.MapStateDescriptor;
import org.apache.flink.api.common.typeinfo.TypeInformation;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.streaming.api.datastream.BroadcastStream;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.datastream.SingleOutputStreamOperator;
import org.apache.flink.streaming.api.functions.co.BroadcastProcessFunction;
import org.apache.flink.util.Collector;
import org.jeasy.rules.api.Facts;

import java.util.ArrayList;
import java.util.List;

@Slf4j
public class FlinkRuleUpdateBroadcast {

    private static final MapStateDescriptor<String, EasyRule> RULE_STATE_DESC =
        new MapStateDescriptor<>("rules-broadcast", 
            TypeInformation.of(String.class), 
            TypeInformation.of(EasyRule.class));

    public DataStream<RuleDecisionResult> createStreamWithRuleBroadcast(
            DataStream<String> eventStream,
            DataStream<String> ruleUpdateStream) {
        
        BroadcastStream<EasyRule> ruleBroadcast = ruleUpdateStream
            .map(json -> JSON.parseObject(json, EasyRule.class))
            .broadcast(RULE_STATE_DESC);
        
        SingleOutputStreamOperator<RuleDecisionResult> resultStream = eventStream
            .connect(ruleBroadcast)
            .process(new RuleBroadcastProcessFunction());
        
        return resultStream;
    }

    public static class RuleBroadcastProcessFunction 
            extends BroadcastProcessFunction<String, EasyRule, RuleDecisionResult> {
        
        private transient DynamicRuleEngine ruleEngine;
        
        @Override
        public void open(Configuration parameters) throws Exception {
            ruleEngine = new DynamicRuleEngine();
            ruleEngine.loadAllRules();
        }
        
        @Override
        public void processElement(String value, ReadOnlyContext ctx, 
                                  Collector<RuleDecisionResult> out) throws Exception {
            try {
                RuleEvent event = JSON.parseObject(value, RuleEvent.class);
                String scene = event.getScene() != null ? event.getScene() : "DEFAULT";
                
                Facts facts = new Facts();
                facts.put("requestId", event.getRequestId());
                facts.put("scene", scene);
                facts.put("data", event.getData());
                facts.put("decision", "PASS");
                facts.put("score", 0);
                facts.put("hitRules", new ArrayList<>());
                
                ruleEngine.fireRules(scene, facts);
                
                RuleDecisionResult result = new RuleDecisionResult();
                result.setRequestId(event.getRequestId());
                result.setDecision((String) facts.get("decision"));
                result.setScore((Integer) facts.get("score"));
                result.setHitRules((List<String>) facts.get("hitRules"));
                result.setRuleVersion(ruleEngine.getRuleVersion(scene));
                
                out.collect(result);
                
            } catch (Exception e) {
                log.error("处理事件失败", e);
            }
        }
        
        @Override
        public void processBroadcastElement(EasyRule rule, Context ctx, 
                                          Collector<RuleDecisionResult> out) throws Exception {
            log.info("收到规则更新: {}", rule.getRuleCode());
            
            BroadcastState<String, EasyRule> broadcastState = ctx.getBroadcastState(RULE_STATE_DESC);
            
            if ("ENABLED".equals(rule.getStatus())) {
                broadcastState.put(rule.getRuleCode(), rule);
                ruleEngine.addRule(rule);
            } else {
                broadcastState.remove(rule.getRuleCode());
                ruleEngine.removeRule(rule.getScene(), rule.getRuleCode());
            }
        }
    }

    public static class RuleEvent {
        private String requestId;
        private String scene;
        private java.util.Map<String, Object> data;
        
        public String getRequestId() { return requestId; }
        public void setRequestId(String requestId) { this.requestId = requestId; }
        public String getScene() { return scene; }
        public void setScene(String scene) { this.scene = scene; }
        public java.util.Map<String, Object> getData() { return data; }
        public void setData(java.util.Map<String, Object> data) { this.data = data; }
    }

    public static class RuleDecisionResult {
        private String requestId;
        private String decision;
        private Integer score;
        private List<String> hitRules;
        private long ruleVersion;
        
        public String getRequestId() { return requestId; }
        public void setRequestId(String requestId) { this.requestId = requestId; }
        public String getDecision() { return decision; }
        public void setDecision(String decision) { this.decision = decision; }
        public Integer getScore() { return score; }
        public void setScore(Integer score) { this.score = score; }
        public List<String> getHitRules() { return hitRules; }
        public void setHitRules(List<String> hitRules) { this.hitRules = hitRules; }
        public long getRuleVersion() { return ruleVersion; }
        public void setRuleVersion(long ruleVersion) { this.ruleVersion = ruleVersion; }
    }
}
