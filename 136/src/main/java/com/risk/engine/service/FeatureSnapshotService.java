package com.risk.engine.service;

import com.alibaba.fastjson.JSON;
import com.risk.engine.dto.DecisionRequest;
import com.risk.engine.dto.DecisionResponse;
import com.risk.engine.entity.FeatureSnapshot;
import com.risk.engine.repository.FeatureSnapshotRepository;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

@Slf4j
@Service
public class FeatureSnapshotService {

    @Autowired
    private FeatureSnapshotRepository snapshotRepository;

    public void saveSnapshot(DecisionRequest request, DecisionResponse response, 
                             Map<String, Object> modelResults) {
        try {
            FeatureSnapshot snapshot = new FeatureSnapshot();
            snapshot.setRequestId(request.getRequestId());
            snapshot.setScene(request.getScene());
            
            Object userId = request.getData().get("userId");
            if (userId != null) {
                snapshot.setUserId(userId.toString());
            }
            
            snapshot.setRawData(JSON.toJSONString(request.getData()));
            snapshot.setCalculatedFeatures(JSON.toJSONString(response.getVariables()));
            
            if (modelResults != null) {
                snapshot.setModelResults(JSON.toJSONString(modelResults));
            }
            
            snapshot.setDecision(response.getDecision());
            snapshot.setScore(response.getScore());
            
            snapshotRepository.save(snapshot);
            log.debug("特征快照保存成功: {}", request.getRequestId());
        } catch (Exception e) {
            log.error("特征快照保存失败: {}", request.getRequestId(), e);
        }
    }

    public Optional<FeatureSnapshot> getSnapshotByRequestId(String requestId) {
        return snapshotRepository.findByRequestId(requestId);
    }

    public Map<String, Object> getFeatureHistory(String requestId) {
        Map<String, Object> result = new HashMap<>();
        Optional<FeatureSnapshot> snapshotOpt = snapshotRepository.findByRequestId(requestId);
        
        if (snapshotOpt.isPresent()) {
            FeatureSnapshot snapshot = snapshotOpt.get();
            result.put("requestId", snapshot.getRequestId());
            result.put("userId", snapshot.getUserId());
            result.put("scene", snapshot.getScene());
            result.put("decision", snapshot.getDecision());
            result.put("score", snapshot.getScore());
            result.put("createTime", snapshot.getCreateTime());
            
            try {
                if (snapshot.getRawData() != null) {
                    result.put("rawData", JSON.parse(snapshot.getRawData()));
                }
                if (snapshot.getCalculatedFeatures() != null) {
                    result.put("calculatedFeatures", JSON.parse(snapshot.getCalculatedFeatures()));
                }
                if (snapshot.getModelResults() != null) {
                    result.put("modelResults", JSON.parse(snapshot.getModelResults()));
                }
            } catch (Exception e) {
                log.warn("JSON解析失败", e);
            }
        }
        
        return result;
    }

    public List<FeatureSnapshot> getUserHistory(String userId, int limit) {
        return snapshotRepository.findByUserIdAndTimeRange(
            userId,
            LocalDateTime.now().minusDays(90),
            LocalDateTime.now()
        );
    }

    public Page<FeatureSnapshot> getUserHistoryPaged(String userId, int page, int size) {
        return snapshotRepository.findByUserId(
            userId,
            PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "createTime"))
        );
    }

    public List<FeatureSnapshot> getSnapshotsByTimeRange(LocalDateTime startTime, 
                                                          LocalDateTime endTime) {
        return snapshotRepository.findByTimeRange(startTime, endTime);
    }

    public Page<FeatureSnapshot> getSnapshotsBySceneAndDecision(String scene, String decision,
                                                                 int page, int size) {
        return snapshotRepository.findBySceneAndDecision(
            scene,
            decision,
            PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "createTime"))
        );
    }

    public List<FeatureSnapshot> getRecentSnapshots(int limit) {
        return snapshotRepository.findRecentSnapshots(limit);
    }

    public Map<String, Object> compareSnapshots(String requestId1, String requestId2) {
        Map<String, Object> result = new HashMap<>();
        
        Optional<FeatureSnapshot> snap1 = getSnapshotByRequestId(requestId1);
        Optional<FeatureSnapshot> snap2 = getSnapshotByRequestId(requestId2);
        
        if (snap1.isPresent() && snap2.isPresent()) {
            Map<String, Object> features1 = parseFeatures(snap1.get().getCalculatedFeatures());
            Map<String, Object> features2 = parseFeatures(snap2.get().getCalculatedFeatures());
            
            Map<String, Object> diffs = new HashMap<>();
            for (String key : features1.keySet()) {
                Object val1 = features1.get(key);
                Object val2 = features2.get(key);
                
                if (val1 != null && !val1.equals(val2)) {
                    Map<String, Object> diff = new HashMap<>();
                    diff.put("value1", val1);
                    diff.put("value2", val2);
                    diffs.put(key, diff);
                }
            }
            
            result.put("snapshot1", getBasicInfo(snap1.get()));
            result.put("snapshot2", getBasicInfo(snap2.get()));
            result.put("featureDiffs", diffs);
            result.put("diffCount", diffs.size());
        }
        
        return result;
    }

    private Map<String, Object> parseFeatures(String json) {
        try {
            if (json != null) {
                return JSON.parseObject(json, Map.class);
            }
        } catch (Exception e) {
            log.warn("特征解析失败", e);
        }
        return new HashMap<>();
    }

    private Map<String, Object> getBasicInfo(FeatureSnapshot snapshot) {
        Map<String, Object> info = new HashMap<>();
        info.put("requestId", snapshot.getRequestId());
        info.put("userId", snapshot.getUserId());
        info.put("scene", snapshot.getScene());
        info.put("decision", snapshot.getDecision());
        info.put("score", snapshot.getScore());
        info.put("createTime", snapshot.getCreateTime());
        return info;
    }
}
