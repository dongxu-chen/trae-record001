package com.risk.engine.service;

import com.alibaba.fastjson.JSON;
import com.risk.engine.entity.DecisionTrace;
import com.risk.engine.repository.DecisionTraceRepository;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;

@Slf4j
@Service
public class DecisionTraceService {

    @Autowired
    private DecisionTraceRepository traceRepository;

    public static final String STEP_WHITELIST_CHECK = "WHITELIST_CHECK";
    public static final String STEP_BLACKLIST_CHECK = "BLACKLIST_CHECK";
    public static final String STEP_FEATURE_CALCULATION = "FEATURE_CALCULATION";
    public static final String STEP_MODEL_EVALUATION = "MODEL_EVALUATION";
    public static final String STEP_RULE_EXECUTION = "RULE_EXECUTION";
    public static final String STEP_FINAL_DECISION = "FINAL_DECISION";

    private final ThreadLocal<List<DecisionTrace>> traceThreadLocal = new ThreadLocal<>();

    public void startTrace(String requestId, String userId, String scene) {
        traceThreadLocal.set(new ArrayList<>());
    }

    public void addTrace(String requestId, String userId, String scene, String step, 
                         String stepDesc, String result, Object detail, Long durationMs) {
        try {
            DecisionTrace trace = new DecisionTrace();
            trace.setRequestId(requestId);
            trace.setUserId(userId);
            trace.setScene(scene);
            trace.setStep(step);
            trace.setStepDesc(stepDesc);
            trace.setResult(result);
            trace.setDurationMs(durationMs);
            
            if (detail != null) {
                if (detail instanceof String) {
                    trace.setDetail((String) detail);
                } else {
                    trace.setDetail(JSON.toJSONString(detail));
                }
            }
            
            traceRepository.save(trace);
            
            List<DecisionTrace> traces = traceThreadLocal.get();
            if (traces != null) {
                traces.add(trace);
            }
        } catch (Exception e) {
            log.error("保存决策轨迹失败", e);
        }
    }

    public void addTrace(String requestId, String userId, String scene, String step, 
                         String stepDesc, String result, Object detail) {
        addTrace(requestId, userId, scene, step, stepDesc, result, detail, null);
    }

    public List<DecisionTrace> getFullTrace(String requestId) {
        return traceRepository.getFullTrace(requestId);
    }

    public Map<String, Object> getTraceDetail(String requestId) {
        Map<String, Object> result = new LinkedHashMap<>();
        List<DecisionTrace> traces = getFullTrace(requestId);
        
        result.put("requestId", requestId);
        result.put("traceCount", traces.size());
        
        List<Map<String, Object>> steps = new ArrayList<>();
        long totalDuration = 0;
        
        for (DecisionTrace trace : traces) {
            Map<String, Object> step = new LinkedHashMap<>();
            step.put("step", trace.getStep());
            step.put("stepDesc", trace.getStepDesc());
            step.put("result", trace.getResult());
            step.put("durationMs", trace.getDurationMs());
            step.put("traceTime", trace.getTraceTime());
            
            try {
                if (trace.getDetail() != null && trace.getDetail().startsWith("{")) {
                    step.put("detail", JSON.parse(trace.getDetail()));
                } else {
                    step.put("detail", trace.getDetail());
                }
            } catch (Exception e) {
                step.put("detail", trace.getDetail());
            }
            
            steps.add(step);
            
            if (trace.getDurationMs() != null) {
                totalDuration += trace.getDurationMs();
            }
        }
        
        result.put("steps", steps);
        result.put("totalDurationMs", totalDuration);
        
        return result;
    }

    public List<DecisionTrace> getUserTraces(String userId, LocalDateTime startTime, 
                                              LocalDateTime endTime) {
        return traceRepository.findByUserIdAndTimeRange(userId, startTime, endTime);
    }

    public List<DecisionTrace> getStepTraces(String step, LocalDateTime startTime, 
                                              LocalDateTime endTime) {
        return traceRepository.findByStepAndTimeRange(step, startTime, endTime);
    }

    public List<String> findRequestIdsByResult(String result, LocalDateTime startTime, 
                                                LocalDateTime endTime) {
        return traceRepository.findRequestIdsByResultAndTimeRange(result, startTime, endTime);
    }

    public void endTrace() {
        traceThreadLocal.remove();
    }

    public List<DecisionTrace> getCurrentThreadTraces() {
        List<DecisionTrace> traces = traceThreadLocal.get();
        return traces != null ? traces : Collections.emptyList();
    }
}
