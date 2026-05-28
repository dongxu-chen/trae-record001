package com.configcenter.server.service;

import com.configcenter.server.entity.ConfigAuditLog;
import com.configcenter.server.entity.ConfigPreValidation;
import com.configcenter.server.repository.ConfigAuditLogRepository;
import com.configcenter.server.repository.ConfigPreValidationRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestTemplate;

import javax.servlet.http.HttpServletRequest;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

@Service
public class ConfigPreValidationService {

    private static final Logger logger = LoggerFactory.getLogger(ConfigPreValidationService.class);

    @Autowired
    private ConfigPreValidationRepository validationRepository;

    @Autowired
    private ConfigAuditLogRepository auditLogRepository;

    @Value("${config.pre-validation.timeout-seconds:60}")
    private int timeoutSeconds;

    private final RestTemplate restTemplate = new RestTemplate();

    @Transactional
    public ConfigPreValidation createValidation(String application, String profile, String label,
                                                  String configContent, String testInstanceUrl,
                                                  String createdBy, HttpServletRequest request) {
        String version = "pre-" + LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMddHHmmss"));

        ConfigPreValidation validation = new ConfigPreValidation();
        validation.setApplication(application);
        validation.setProfile(profile);
        validation.setLabel(label);
        validation.setVersion(version);
        validation.setConfigContent(configContent);
        validation.setTestInstanceUrl(testInstanceUrl);
        validation.setCreatedBy(createdBy);
        validation.setStatus(ConfigPreValidation.ValidationStatus.PENDING);

        ConfigPreValidation saved = validationRepository.save(validation);

        saveAuditLog(application, profile, label,
                ConfigAuditLog.ActionType.CREATE,
                null, configContent, null, version,
                createdBy, getClientIp(request),
                "创建配置预校验, 测试实例: " + testInstanceUrl);

        return saved;
    }

    @Transactional
    public ConfigPreValidation executeValidation(Long validationId, HttpServletRequest request) {
        ConfigPreValidation validation = validationRepository.findById(validationId)
                .orElseThrow(() -> new RuntimeException("预校验任务不存在: " + validationId));

        validation.setStatus(ConfigPreValidation.ValidationStatus.RUNNING);
        validationRepository.save(validation);

        new Thread(() -> doValidation(validation)).start();

        return validation;
    }

    private void doValidation(ConfigPreValidation validation) {
        try {
            logger.info("开始执行配置预校验: application={}, testInstance={}",
                    validation.getApplication(), validation.getTestInstanceUrl());

            Map<String, Object> validationResult = new HashMap<>();
            validationResult.put("startTime", LocalDateTime.now().toString());
            validationResult.put("application", validation.getApplication());

            boolean yamlValid = validateYamlFormat(validation.getConfigContent());
            validationResult.put("yamlFormatValid", yamlValid);

            if (!yamlValid) {
                validationResult.put("error", "YAML格式校验失败");
                validationResult.put("passed", false);
                finishValidation(validation, validationResult, ConfigPreValidation.ValidationStatus.FAILED);
                return;
            }

            boolean instanceReachable = testInstanceReachable(validation.getTestInstanceUrl());
            validationResult.put("instanceReachable", instanceReachable);

            if (!instanceReachable) {
                validationResult.put("error", "测试实例不可达");
                validationResult.put("passed", false);
                finishValidation(validation, validationResult, ConfigPreValidation.ValidationStatus.FAILED);
                return;
            }

            boolean configApplied = applyConfigToTestInstance(validation);
            validationResult.put("configApplied", configApplied);

            if (!configApplied) {
                validationResult.put("error", "配置应用到测试实例失败");
                validationResult.put("passed", false);
                finishValidation(validation, validationResult, ConfigPreValidation.ValidationStatus.FAILED);
                return;
            }

            boolean healthCheckPassed = performHealthCheck(validation.getTestInstanceUrl());
            validationResult.put("healthCheckPassed", healthCheckPassed);

            if (!healthCheckPassed) {
                validationResult.put("error", "健康检查失败");
                validationResult.put("passed", false);
                finishValidation(validation, validationResult, ConfigPreValidation.ValidationStatus.FAILED);
                return;
            }

            boolean functionTestPassed = performFunctionTest(validation.getTestInstanceUrl());
            validationResult.put("functionTestPassed", functionTestPassed);

            validationResult.put("passed", functionTestPassed);
            validationResult.put("endTime", LocalDateTime.now().toString());

            ConfigPreValidation.ValidationStatus status = functionTestPassed
                    ? ConfigPreValidation.ValidationStatus.PASSED
                    : ConfigPreValidation.ValidationStatus.FAILED;

            finishValidation(validation, validationResult, status);

        } catch (Exception e) {
            logger.error("预校验执行异常", e);
            Map<String, Object> errorResult = new HashMap<>();
            errorResult.put("error", e.getMessage());
            errorResult.put("passed", false);
            finishValidation(validation, errorResult, ConfigPreValidation.ValidationStatus.FAILED);
        }
    }

    private void finishValidation(ConfigPreValidation validation,
                                   Map<String, Object> result,
                                   ConfigPreValidation.ValidationStatus status) {
        validation.setValidationResult(result.toString());
        validation.setStatus(status);
        validation.setEndTime(LocalDateTime.now());
        validationRepository.save(validation);

        logger.info("预校验完成: application={}, status={}, passed={}",
                validation.getApplication(), status, result.get("passed"));
    }

    private boolean validateYamlFormat(String configContent) {
        try {
            if (configContent == null || configContent.trim().isEmpty()) {
                return false;
            }
            String[] lines = configContent.split("\n");
            for (String line : lines) {
                String trimmed = line.trim();
                if (trimmed.isEmpty() || trimmed.startsWith("#")) continue;
                if (trimmed.contains(":") && !trimmed.startsWith("-")) {
                    String[] parts = trimmed.split(":", 2);
                    if (parts.length < 2) return false;
                }
            }
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    private boolean testInstanceReachable(String testInstanceUrl) {
        try {
            String healthUrl = testInstanceUrl + "/actuator/health";
            ResponseEntity<String> response = restTemplate.getForEntity(healthUrl, String.class);
            return response.getStatusCode().is2xxSuccessful();
        } catch (Exception e) {
            logger.warn("测试实例不可达: {}", e.getMessage());
            return false;
        }
    }

    private boolean applyConfigToTestInstance(ConfigPreValidation validation) {
        try {
            String refreshUrl = validation.getTestInstanceUrl() + "/actuator/refresh";
            Map<String, String> request = new HashMap<>();
            request.put("configContent", validation.getConfigContent());
            ResponseEntity<String> response = restTemplate.postForEntity(
                    refreshUrl, request, String.class);
            return response.getStatusCode().is2xxSuccessful();
        } catch (Exception e) {
            logger.warn("配置应用失败: {}", e.getMessage());
            return false;
        }
    }

    private boolean performHealthCheck(String testInstanceUrl) {
        try {
            Thread.sleep(2000);
            String healthUrl = testInstanceUrl + "/actuator/health";
            ResponseEntity<String> response = restTemplate.getForEntity(healthUrl, String.class);
            if (response.getStatusCode().is2xxSuccessful() && response.getBody() != null) {
                return response.getBody().contains("\"status\":\"UP\"");
            }
            return false;
        } catch (Exception e) {
            logger.warn("健康检查失败: {}", e.getMessage());
            return false;
        }
    }

    private boolean performFunctionTest(String testInstanceUrl) {
        try {
            String configUrl = testInstanceUrl + "/api/config/current";
            ResponseEntity<String> response = restTemplate.getForEntity(configUrl, String.class);
            return response.getStatusCode().is2xxSuccessful();
        } catch (Exception e) {
            logger.warn("功能测试失败: {}", e.getMessage());
            return false;
        }
    }

    public List<ConfigPreValidation> getValidationHistory(String application) {
        return validationRepository.findByApplicationOrderByStartTimeDesc(application);
    }

    public List<ConfigPreValidation> getValidations(String application, String profile, String label) {
        return validationRepository.findByApplicationAndProfileAndLabelOrderByStartTimeDesc(
                application, profile, label);
    }

    public List<ConfigPreValidation> getActiveValidations(String application) {
        return validationRepository.findActiveValidations(application);
    }

    public Optional<ConfigPreValidation> getValidation(Long id) {
        return validationRepository.findById(id);
    }

    @Transactional
    public ConfigPreValidation cancelValidation(Long validationId, String operator,
                                                  HttpServletRequest request) {
        ConfigPreValidation validation = validationRepository.findById(validationId)
                .orElseThrow(() -> new RuntimeException("预校验任务不存在: " + validationId));

        validation.setStatus(ConfigPreValidation.ValidationStatus.CANCELLED);
        validation.setEndTime(LocalDateTime.now());
        ConfigPreValidation saved = validationRepository.save(validation);

        saveAuditLog(validation.getApplication(), validation.getProfile(),
                validation.getLabel(),
                ConfigAuditLog.ActionType.UPDATE,
                null, null, null, validation.getVersion(),
                operator, getClientIp(request),
                "取消预校验任务: " + validationId);

        return saved;
    }

    private void saveAuditLog(String application, String profile, String label,
                               ConfigAuditLog.ActionType action,
                               String oldValue, String newValue,
                               String versionBefore, String versionAfter,
                               String operator, String operatorIp, String remark) {
        ConfigAuditLog auditLog = new ConfigAuditLog();
        auditLog.setApplication(application);
        auditLog.setProfile(profile);
        auditLog.setLabel(label);
        auditLog.setAction(action);
        auditLog.setOldValue(oldValue);
        auditLog.setNewValue(newValue);
        auditLog.setVersionBefore(versionBefore);
        auditLog.setVersionAfter(versionAfter);
        auditLog.setOperator(operator);
        auditLog.setOperatorIp(operatorIp);
        auditLog.setRemark(remark);
        auditLogRepository.save(auditLog);
    }

    private String getClientIp(HttpServletRequest request) {
        if (request == null) {
            return "unknown";
        }
        String ip = request.getHeader("X-Forwarded-For");
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("X-Real-IP");
        }
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getRemoteAddr();
        }
        return ip;
    }
}
