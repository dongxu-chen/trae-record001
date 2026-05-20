package com.risk.engine.service;

import com.risk.engine.config.DroolsConfig;
import com.risk.engine.dto.DecisionRequest;
import com.risk.engine.dto.DecisionResponse;
import com.risk.engine.model.RiskFact;
import lombok.extern.slf4j.Slf4j;
import org.kie.api.runtime.KieSession;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.*;

@Slf4j
@Service
public class DecisionService {

    @Autowired
    private DroolsConfig droolsConfig;

    @Autowired
    private VariableService variableService;

    @Autowired
    private RiskListService riskListService;

    @Autowired
    private PmmlModelService pmmlModelService;

    @Autowired
    private FeatureSnapshotService snapshotService;

    @Autowired
    private DecisionTraceService traceService;

    public DecisionResponse makeDecision(DecisionRequest request) {
        long startTime = System.currentTimeMillis();
        DecisionResponse response = new DecisionResponse();
        Map<String, Object> modelResults = new HashMap<>();
        String userId = request.getData() != null ? 
            String.valueOf(request.getData().getOrDefault("userId", "")) : "";
        
        try {
            String requestId = request.getRequestId() != null ? 
                    request.getRequestId() : UUID.randomUUID().toString();
            response.setRequestId(requestId);
            
            traceService.startTrace(requestId, userId, request.getScene());
            
            RiskFact fact = buildRiskFact(request);
            
            long stepStart = System.currentTimeMillis();
            List<String> whitelistMatch = riskListService.matchLists(request.getData(), "WHITELIST");
            long stepDuration = System.currentTimeMillis() - stepStart;
            traceService.addTrace(requestId, userId, request.getScene(),
                    DecisionTraceService.STEP_WHITELIST_CHECK,
                    "白名单匹配",
                    whitelistMatch.isEmpty() ? "未命中" : "命中",
                    whitelistMatch, stepDuration);
            
            if (!whitelistMatch.isEmpty()) {
                fact.setDecision("PASS");
                fact.addHitRule("WHITELIST_PASS");
                log.info("请求 [{}] 命中白名单, 直接通过", requestId);
            } else {
                stepStart = System.currentTimeMillis();
                List<String> blacklistMatch = riskListService.matchLists(request.getData(), "BLACKLIST");
                stepDuration = System.currentTimeMillis() - stepStart;
                traceService.addTrace(requestId, userId, request.getScene(),
                        DecisionTraceService.STEP_BLACKLIST_CHECK,
                        "黑名单匹配",
                        blacklistMatch.isEmpty() ? "未命中" : "命中",
                        blacklistMatch, stepDuration);
                
                if (!blacklistMatch.isEmpty()) {
                    fact.setDecision("REJECT");
                    fact.addHitRule("BLACKLIST_REJECT");
                    log.info("请求 [{}] 命中黑名单, 直接拒绝", requestId);
                } else {
                    stepStart = System.currentTimeMillis();
                    Map<String, Object> variables = variableService.calculateVariables(request.getData());
                    fact.getVariables().putAll(variables);
                    response.setVariables(variables);
                    stepDuration = System.currentTimeMillis() - stepStart;
                    traceService.addTrace(requestId, userId, request.getScene(),
                            DecisionTraceService.STEP_FEATURE_CALCULATION,
                            "特征变量计算",
                            "完成",
                            variables.keySet(), stepDuration);
                    
                    stepStart = System.currentTimeMillis();
                    try {
                        modelResults = pmmlModelService.evaluateByScene(request.getScene(), variables);
                        stepDuration = System.currentTimeMillis() - stepStart;
                        traceService.addTrace(requestId, userId, request.getScene(),
                                DecisionTraceService.STEP_MODEL_EVALUATION,
                                "机器学习模型评估",
                                "完成",
                                modelResults.keySet(), stepDuration);
                        
                        if (modelResults.containsKey("ensembleScore")) {
                            Double ensembleScore = (Double) modelResults.get("ensembleScore");
                            fact.setScore(ensembleScore.intValue());
                        }
                    } catch (Exception e) {
                        log.warn("模型评估异常: {}", e.getMessage());
                    }
                    
                    String scene = request.getScene() != null ? request.getScene() : "DEFAULT";
                    stepStart = System.currentTimeMillis();
                    executeDroolsRules(scene, fact);
                    stepDuration = System.currentTimeMillis() - stepStart;
                    traceService.addTrace(requestId, userId, request.getScene(),
                            DecisionTraceService.STEP_RULE_EXECUTION,
                            "规则引擎执行",
                            "完成",
                            fact.getHitRules(), stepDuration);
                }
            }
            
            response.setDecision(fact.getDecision());
            response.setScore(fact.getScore());
            response.setHitRules(new ArrayList<>(fact.getHitRules()));
            response.setMatchedLists(new ArrayList<>(fact.getMatchedLists()));
            response.setRuleVersion(droolsConfig.getContainerVersion(request.getScene()));
            
            stepStart = System.currentTimeMillis();
            snapshotService.saveSnapshot(request, response, modelResults);
            stepDuration = System.currentTimeMillis() - stepStart;
            traceService.addTrace(requestId, userId, request.getScene(),
                    DecisionTraceService.STEP_FINAL_DECISION,
                    "最终决策",
                    fact.getDecision(),
                    null, stepDuration);
            
        } catch (Exception e) {
            log.error("决策执行异常, 请求ID: {}", request.getRequestId(), e);
            response.setDecision("ERROR");
            response.setErrorMsg(e.getMessage());
        } finally {
            traceService.endTrace();
            long executeTime = System.currentTimeMillis() - startTime;
            response.setExecuteTime(executeTime);
            log.info("决策请求: {}, 场景: {}, 决策结果: {}, 耗时: {}ms, 命中规则: {}", 
                    response.getRequestId(), request.getScene(), 
                    response.getDecision(), executeTime, response.getHitRules());
        }
        
        return response;
    }

    private RiskFact buildRiskFact(DecisionRequest request) {
        RiskFact fact = new RiskFact();
        fact.setRequestId(request.getRequestId());
        fact.setScene(request.getScene());
        fact.setData(request.getData());
        return fact;
    }

    private void executeDroolsRules(String scene, RiskFact fact) {
        KieSession kieSession = null;
        try {
            kieSession = droolsConfig.getKieSession(scene);
            kieSession.insert(fact);
            int firedRules = kieSession.fireAllRules();
            log.debug("场景 [{}] 执行完成, 触发规则数: {}", scene, firedRules);
        } finally {
            if (kieSession != null) {
                try {
                    kieSession.dispose();
                } catch (Exception e) {
                    log.warn("KieSession释放异常: {}", e.getMessage());
                }
            }
        }
    }

    public boolean reloadRules(String scene, String rulesContent) {
        return droolsConfig.reloadRules(scene, rulesContent);
    }

    public Long getRuleVersion(String scene) {
        return droolsConfig.getContainerVersion(scene);
    }
}
