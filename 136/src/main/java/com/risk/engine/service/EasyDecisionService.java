package com.risk.engine.service;

import com.risk.engine.dto.DecisionRequest;
import com.risk.engine.dto.DecisionResponse;
import com.risk.engine.rules.DynamicRuleEngine;
import lombok.extern.slf4j.Slf4j;
import org.jeasy.rules.api.Facts;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.*;

@Slf4j
@Service
public class EasyDecisionService {

    @Autowired
    private DynamicRuleEngine ruleEngine;

    @Autowired
    private VariableService variableService;

    @Autowired
    private RiskListService riskListService;

    @Autowired
    private FeatureSnapshotService snapshotService;

    @Autowired
    private DecisionTraceService traceService;

    public DecisionResponse makeDecision(DecisionRequest request) {
        long startTime = System.currentTimeMillis();
        DecisionResponse response = new DecisionResponse();
        String userId = request.getData() != null ? 
            String.valueOf(request.getData().getOrDefault("userId", "")) : "";
        String requestId = request.getRequestId() != null ? 
            request.getRequestId() : UUID.randomUUID().toString();
        String scene = request.getScene() != null ? request.getScene() : "DEFAULT";
        
        try {
            response.setRequestId(requestId);
            
            traceService.startTrace(requestId, userId, scene);
            
            Facts facts = new Facts();
            facts.put("requestId", requestId);
            facts.put("scene", scene);
            facts.put("data", request.getData());
            facts.put("decision", "PASS");
            facts.put("score", 0);
            facts.put("hitRules", new ArrayList<>());
            facts.put("matchedLists", new ArrayList<>());
            
            long stepStart = System.currentTimeMillis();
            List<String> whitelistMatch = riskListService.matchLists(request.getData(), "WHITELIST");
            long stepDuration = System.currentTimeMillis() - stepStart;
            traceService.addTrace(requestId, userId, scene,
                    DecisionTraceService.STEP_WHITELIST_CHECK,
                    "白名单匹配",
                    whitelistMatch.isEmpty() ? "未命中" : "命中",
                    whitelistMatch, stepDuration);
            
            if (!whitelistMatch.isEmpty()) {
                facts.put("decision", "PASS");
                ((List<String>) facts.get("hitRules")).add("WHITELIST_PASS");
                ((List<String>) facts.get("matchedLists")).addAll(whitelistMatch);
            } else {
                stepStart = System.currentTimeMillis();
                List<String> blacklistMatch = riskListService.matchLists(request.getData(), "BLACKLIST");
                stepDuration = System.currentTimeMillis() - stepStart;
                traceService.addTrace(requestId, userId, scene,
                        DecisionTraceService.STEP_BLACKLIST_CHECK,
                        "黑名单匹配",
                        blacklistMatch.isEmpty() ? "未命中" : "命中",
                        blacklistMatch, stepDuration);
                
                if (!blacklistMatch.isEmpty()) {
                    facts.put("decision", "REJECT");
                    facts.put("score", 100);
                    ((List<String>) facts.get("hitRules")).add("BLACKLIST_REJECT");
                    ((List<String>) facts.get("matchedLists")).addAll(blacklistMatch);
                } else {
                    stepStart = System.currentTimeMillis();
                    Map<String, Object> variables = variableService.calculateVariables(request.getData());
                    facts.put("variables", variables);
                    stepDuration = System.currentTimeMillis() - stepStart;
                    traceService.addTrace(requestId, userId, scene,
                            DecisionTraceService.STEP_FEATURE_CALCULATION,
                            "特征变量计算",
                            "完成",
                            variables.keySet(), stepDuration);
                    
                    for (Map.Entry<String, Object> entry : variables.entrySet()) {
                        facts.put(entry.getKey(), entry.getValue());
                    }
                    
                    stepStart = System.currentTimeMillis();
                    ruleEngine.fireRules(scene, facts);
                    stepDuration = System.currentTimeMillis() - stepStart;
                    traceService.addTrace(requestId, userId, scene,
                            DecisionTraceService.STEP_RULE_EXECUTION,
                            "规则引擎执行",
                            "完成",
                            facts.get("hitRules"), stepDuration);
                }
            }
            
            response.setDecision((String) facts.get("decision"));
            response.setScore((Integer) facts.get("score"));
            response.setHitRules((List<String>) facts.get("hitRules"));
            response.setMatchedLists((List<String>) facts.get("matchedLists"));
            response.setVariables((Map<String, Object>) facts.get("variables"));
            response.setRuleVersion(ruleEngine.getRuleVersion(scene));
            
            stepStart = System.currentTimeMillis();
            snapshotService.saveSnapshot(request, response, null);
            stepDuration = System.currentTimeMillis() - stepStart;
            traceService.addTrace(requestId, userId, scene,
                    DecisionTraceService.STEP_FINAL_DECISION,
                    "最终决策",
                    response.getDecision(),
                    null, stepDuration);
            
        } catch (Exception e) {
            log.error("决策执行异常, 请求ID: {}", requestId, e);
            response.setDecision("ERROR");
            response.setErrorMsg(e.getMessage());
        } finally {
            traceService.endTrace();
            long executeTime = System.currentTimeMillis() - startTime;
            response.setExecuteTime(executeTime);
            log.info("决策请求: {}, 场景: {}, 决策结果: {}, 耗时: {}ms, 命中规则: {}", 
                    response.getRequestId(), scene, 
                    response.getDecision(), executeTime, response.getHitRules());
        }
        
        return response;
    }

    public boolean reloadRules(String scene) {
        return ruleEngine.reloadRules(scene);
    }

    public boolean reloadAllRules() {
        return ruleEngine.reloadAllRules();
    }

    public long getRuleVersion(String scene) {
        return ruleEngine.getRuleVersion(scene);
    }

    public Map<String, Object> getEngineStatus() {
        Map<String, Object> status = new HashMap<>();
        Set<String> scenes = ruleEngine.getRegisteredScenes();
        status.put("sceneCount", scenes.size());
        status.put("scenes", scenes);
        
        Map<String, Integer> ruleCounts = new HashMap<>();
        for (String scene : scenes) {
            ruleCounts.put(scene, ruleEngine.getRuleCount(scene));
        }
        status.put("ruleCounts", ruleCounts);
        
        return status;
    }
}
