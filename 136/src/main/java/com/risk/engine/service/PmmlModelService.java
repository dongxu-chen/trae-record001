package com.risk.engine.service;

import com.alibaba.fastjson.JSON;
import com.risk.engine.entity.MlModel;
import com.risk.engine.repository.MlModelRepository;
import lombok.extern.slf4j.Slf4j;
import org.dmg.pmml.PMML;
import org.jpmml.evaluator.*;
import org.jpmml.model.PMMLUtil;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.io.support.PathMatchingResourcePatternResolver;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import javax.annotation.PostConstruct;
import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

@Slf4j
@Service
public class PmmlModelService {

    @Autowired
    private MlModelRepository mlModelRepository;

    private final ConcurrentHashMap<String, ModelEvaluator<?>> evaluatorCache = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, MlModel> modelMetaCache = new ConcurrentHashMap<>();

    @PostConstruct
    public void init() {
        try {
            log.info("开始初始化PMML模型...");
            loadModelsFromClasspath();
            loadModelsFromDatabase();
            log.info("PMML模型初始化完成，共加载 {} 个模型", evaluatorCache.size());
        } catch (Exception e) {
            log.error("PMML模型初始化失败", e);
        }
    }

    private void loadModelsFromClasspath() {
        try {
            PathMatchingResourcePatternResolver resolver = new PathMatchingResourcePatternResolver();
            org.springframework.core.io.Resource[] resources = resolver.getResources("classpath*:models/*.pmml");
            for (org.springframework.core.io.Resource resource : resources) {
                try {
                    String fileName = resource.getFilename();
                    if (fileName == null) continue;
                    String modelCode = fileName.replace(".pmml", "");
                    log.info("加载PMML模型: {}", modelCode);
                    loadModel(modelCode, resource.getInputStream());
                } catch (Exception e) {
                    log.error("加载PMML模型失败: {}", resource.getFilename(), e);
                }
            }
        } catch (Exception e) {
            log.error("扫描classpath模型文件失败", e);
        }
    }

    private void loadModelsFromDatabase() {
        List<MlModel> models = mlModelRepository.findByStatus("ENABLED");
        for (MlModel model : models) {
            try {
                if (model.getModelContent() != null && model.getModelContent().length > 0) {
                    loadModel(model.getModelCode(), new ByteArrayInputStream(model.getModelContent()));
                    modelMetaCache.put(model.getModelCode(), model);
                }
            } catch (Exception e) {
                log.error("加载数据库模型失败: {}", model.getModelCode(), e);
            }
        }
    }

    public void loadModel(String modelCode, InputStream inputStream) throws Exception {
        PMML pmml = PMMLUtil.unmarshal(inputStream);
        ModelEvaluatorBuilder evaluatorBuilder = new ModelEvaluatorBuilder(pmml);
        ModelEvaluator<?> evaluator = evaluatorBuilder.build();
        evaluator.verify();
        evaluatorCache.put(modelCode, evaluator);
        log.info("PMML模型加载成功: {}", modelCode);
    }

    public Map<String, Object> evaluate(String modelCode, Map<String, Object> features) {
        ModelEvaluator<?> evaluator = evaluatorCache.get(modelCode);
        if (evaluator == null) {
            throw new RuntimeException("模型不存在: " + modelCode);
        }

        Map<String, Object> result = new HashMap<>();
        try {
            Map<FieldName, FieldValue> arguments = new LinkedHashMap<>();
            List<? extends InputField> inputFields = evaluator.getInputFields();

            for (InputField inputField : inputFields) {
                FieldName inputFieldName = inputField.getName();
                Object rawValue = features.get(inputFieldName.getValue());
                FieldValue inputFieldValue = inputField.prepare(rawValue);
                arguments.put(inputFieldName, inputFieldValue);
            }

            Map<FieldName, ?> results = evaluator.evaluate(arguments);
            List<? extends TargetField> targetFields = evaluator.getTargetFields();
            List<? extends OutputField> outputFields = evaluator.getOutputFields();

            for (TargetField targetField : targetFields) {
                FieldName targetFieldName = targetField.getName();
                Object targetFieldValue = results.get(targetFieldName);
                result.put(targetFieldName.getValue(), EvaluatorUtil.decode(targetFieldValue));
            }

            for (OutputField outputField : outputFields) {
                FieldName outputFieldName = outputField.getName();
                Object outputFieldValue = results.get(outputFieldName);
                result.put(outputFieldName.getValue(), EvaluatorUtil.decode(outputFieldValue));
            }

            MlModel model = modelMetaCache.get(modelCode);
            if (model != null && model.getThreshold() != null) {
                Double score = getScoreFromResult(result);
                if (score != null) {
                    result.put("threshold", model.getThreshold());
                    result.put("decision", score >= model.getThreshold() ? "REJECT" : "PASS");
                }
            }

        } catch (Exception e) {
            log.error("模型评估失败: {}, 特征: {}", modelCode, JSON.toJSONString(features), e);
            throw new RuntimeException("模型评估失败: " + e.getMessage());
        }

        return result;
    }

    private Double getScoreFromResult(Map<String, Object> result) {
        for (Map.Entry<String, Object> entry : result.entrySet()) {
            if (entry.getValue() instanceof Number) {
                return ((Number) entry.getValue()).doubleValue();
            }
            if ("probability".equalsIgnoreCase(entry.getKey()) || 
                "score".equalsIgnoreCase(entry.getKey()) ||
                "prediction".equalsIgnoreCase(entry.getKey())) {
                try {
                    return Double.parseDouble(entry.getValue().toString());
                } catch (Exception ignored) {
                }
            }
        }
        return null;
    }

    public Map<String, Object> evaluateByScene(String scene, Map<String, Object> features) {
        Map<String, Object> result = new HashMap<>();
        List<MlModel> models = modelMetaCache.values().stream()
                .filter(m -> scene.equals(m.getScene()) && "ENABLED".equals(m.getStatus()))
                .collect(Collectors.toList());

        double totalScore = 0.0;
        double totalWeight = 0.0;

        for (MlModel model : models) {
            try {
                Map<String, Object> modelResult = evaluate(model.getModelCode(), features);
                result.put(model.getModelCode(), modelResult);
                Double score = getScoreFromResult(modelResult);
                if (score != null) {
                    totalScore += score * model.getWeight();
                    totalWeight += model.getWeight();
                }
            } catch (Exception e) {
                log.warn("模型评估失败: {}", model.getModelCode(), e);
            }
        }

        if (totalWeight > 0) {
            result.put("ensembleScore", totalScore / totalWeight);
        }

        return result;
    }

    public MlModel saveModel(MlModel model, MultipartFile file) throws Exception {
        if (file != null && !file.isEmpty()) {
            model.setModelContent(file.getBytes());
            try (InputStream is = new ByteArrayInputStream(file.getBytes())) {
                loadModel(model.getModelCode(), is);
            }
        }
        MlModel saved = mlModelRepository.save(model);
        if ("ENABLED".equals(saved.getStatus())) {
            modelMetaCache.put(saved.getModelCode(), saved);
        }
        return saved;
    }

    public void deleteModel(Long id) {
        MlModel model = mlModelRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("模型不存在"));
        evaluatorCache.remove(model.getModelCode());
        modelMetaCache.remove(model.getModelCode());
        mlModelRepository.deleteById(id);
    }

    public MlModel updateModelStatus(Long id, String status) {
        MlModel model = mlModelRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("模型不存在"));
        model.setStatus(status);
        MlModel updated = mlModelRepository.save(model);
        if ("ENABLED".equals(status)) {
            modelMetaCache.put(updated.getModelCode(), updated);
        } else {
            modelMetaCache.remove(updated.getModelCode());
        }
        return updated;
    }

    public List<String> getModelFeatures(String modelCode) {
        ModelEvaluator<?> evaluator = evaluatorCache.get(modelCode);
        if (evaluator == null) {
            return Collections.emptyList();
        }
        return evaluator.getInputFields().stream()
                .map(f -> f.getName().getValue())
                .collect(Collectors.toList());
    }

    public Set<String> getLoadedModelCodes() {
        return evaluatorCache.keySet();
    }

    public Optional<MlModel> getModelById(Long id) {
        return mlModelRepository.findById(id);
    }

    public List<MlModel> getAllModels() {
        return mlModelRepository.findAll();
    }
}
