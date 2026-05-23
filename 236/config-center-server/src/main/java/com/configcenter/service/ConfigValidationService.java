package com.configcenter.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.dataformat.yaml.YAMLMapper;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;

@Service
public class ConfigValidationService {

    private final ObjectMapper jsonMapper = new ObjectMapper();
    private final YAMLMapper yamlMapper = new YAMLMapper();

    public ValidationResult validate(String content, String format) {
        if (content == null || content.trim().isEmpty()) {
            return ValidationResult.error("配置内容不能为空");
        }

        if ("json".equalsIgnoreCase(format)) {
            return validateJson(content);
        } else if ("yml".equalsIgnoreCase(format) || "yaml".equalsIgnoreCase(format)) {
            return validateYaml(content);
        } else {
            return ValidationResult.error("不支持的格式: " + format + "，请使用 json 或 yaml");
        }
    }

    private ValidationResult validateJson(String content) {
        try {
            jsonMapper.readTree(content);
            return ValidationResult.success();
        } catch (JsonProcessingException e) {
            List<String> errors = new ArrayList<>();
            errors.add("JSON语法错误: " + e.getOriginalMessage());
            if (e.getLocation() != null) {
                errors.add("位置: 第 " + e.getLocation().getLineNr() + " 行, 第 " + e.getLocation().getColumnNr() + " 列");
            }
            return ValidationResult.error(errors);
        }
    }

    private ValidationResult validateYaml(String content) {
        try {
            yamlMapper.readTree(content);
            return ValidationResult.success();
        } catch (JsonProcessingException e) {
            List<String> errors = new ArrayList<>();
            errors.add("YAML语法错误: " + e.getOriginalMessage());
            if (e.getLocation() != null) {
                errors.add("位置: 第 " + e.getLocation().getLineNr() + " 行, 第 " + e.getLocation().getColumnNr() + " 列");
            }
            return ValidationResult.error(errors);
        }
    }

    public String convertToJson(String yamlContent) throws JsonProcessingException {
        JsonNode node = yamlMapper.readTree(yamlContent);
        return jsonMapper.writerWithDefaultPrettyPrinter().writeValueAsString(node);
    }

    public String convertToYaml(String jsonContent) throws JsonProcessingException {
        JsonNode node = jsonMapper.readTree(jsonContent);
        return yamlMapper.writerWithDefaultPrettyPrinter().writeValueAsString(node);
    }

    public static class ValidationResult {
        private boolean valid;
        private List<String> errors;

        private ValidationResult(boolean valid, List<String> errors) {
            this.valid = valid;
            this.errors = errors;
        }

        public static ValidationResult success() {
            return new ValidationResult(true, new ArrayList<>());
        }

        public static ValidationResult error(String error) {
            List<String> errors = new ArrayList<>();
            errors.add(error);
            return new ValidationResult(false, errors);
        }

        public static ValidationResult error(List<String> errors) {
            return new ValidationResult(false, errors);
        }

        public boolean isValid() {
            return valid;
        }

        public List<String> getErrors() {
            return errors;
        }
    }
}
