package com.api.docs.generator;

import com.api.docs.model.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

public class ExampleGenerator {
    private static final Logger logger = LoggerFactory.getLogger(ExampleGenerator.class);
    private static final Random RANDOM = new Random();
    private static final DateTimeFormatter DATE_FORMAT = DateTimeFormatter.ofPattern("yyyy-MM-dd");
    private static final DateTimeFormatter DATETIME_FORMAT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    private final Map<String, ModelInfo> modelMap = new HashMap<>();
    private final Map<String, Object> generatedExamples = new HashMap<>();

    public ExampleGenerator(List<ModelInfo> models) {
        for (ModelInfo model : models) {
            modelMap.put(model.getClassName(), model);
        }
    }

    public void generateForApi(ApiInfo apiInfo) {
        logger.info("开始生成API示例");
        for (ControllerInfo controller : apiInfo.getControllers()) {
            for (MethodInfo method : controller.getMethods()) {
                try {
                    if (method.getRequestBodyType() != null && !method.getRequestBodyType().isEmpty()) {
                        Object requestExample = generateExampleForType(method.getRequestBodyType());
                        method.setRequestBodyExample(requestExample);
                    }
                    if (method.getResponseType() != null && !method.getResponseType().isEmpty()
                            && !method.getResponseType().equals("void")
                            && !method.getResponseType().equals("Void")) {
                        Object responseExample = generateExampleForType(method.getResponseType());
                        method.setResponseExample(responseExample);
                    }
                    for (ParameterInfo param : method.getParameters()) {
                        if (param.getExample() == null || param.getExample().isEmpty()) {
                            param.setExample(generateSimpleExample(param.getType()));
                        }
                    }
                } catch (Exception e) {
                    logger.warn("生成示例失败: {} {}", method.getHttpMethod(), method.getPath(), e);
                }
            }
        }
        logger.info("API示例生成完成");
    }

    public Object generateExampleForType(String typeName) {
        if (typeName == null || typeName.isEmpty()) {
            return null;
        }
        return generateExampleForType(typeName, new HashSet<>(), 0);
    }

    private Object generateExampleForType(String typeName, Set<String> visited, int depth) {
        if (depth > 5) {
            return null;
        }

        typeName = typeName.trim();

        if (generatedExamples.containsKey(typeName)) {
            return generatedExamples.get(typeName);
        }

        if (typeName.startsWith("List<") || typeName.startsWith("Set<") || typeName.startsWith("Collection<")) {
            int start = typeName.indexOf('<');
            int end = typeName.lastIndexOf('>');
            if (start > 0 && end > start) {
                String innerType = typeName.substring(start + 1, end);
                List<Object> list = new ArrayList<>();
                Object item = generateExampleForType(innerType, visited, depth + 1);
                if (item != null) {
                    list.add(item);
                    list.add(item);
                }
                return list;
            }
        }

        if (typeName.startsWith("Page<") || typeName.startsWith("IPage<")) {
            int start = typeName.indexOf('<');
            int end = typeName.lastIndexOf('>');
            String innerType = start > 0 && end > start ? typeName.substring(start + 1, end) : "Object";
            Map<String, Object> page = new LinkedHashMap<>();
            page.put("total", 100L);
            page.put("size", 10);
            page.put("current", 1);
            page.put("pages", 10);
            List<Object> records = new ArrayList<>();
            Object item = generateExampleForType(innerType, visited, depth + 1);
            if (item != null) {
                records.add(item);
                records.add(item);
            }
            page.put("records", records);
            return page;
        }

        if (typeName.startsWith("Map<")) {
            return new LinkedHashMap<>();
        }

        Object simpleExample = generateSimpleExample(typeName);
        if (simpleExample != null) {
            return simpleExample;
        }

        String cleanType = typeName.replace("[]", "").trim();
        if (visited.contains(cleanType)) {
            return null;
        }
        visited.add(cleanType);

        ModelInfo modelInfo = modelMap.get(cleanType);
        if (modelInfo == null) {
            visited.remove(cleanType);
            return null;
        }

        Map<String, Object> example = new LinkedHashMap<>();
        for (FieldInfo field : modelInfo.getFields()) {
            if (field.getExample() != null && !field.getExample().isEmpty()) {
                example.put(field.getName(), parseExampleValue(field.getExample(), field.getType()));
            } else {
                Object fieldExample = generateExampleForType(field.getType(), visited, depth + 1);
                example.put(field.getName(), fieldExample != null ? fieldExample : null);
            }
        }

        visited.remove(cleanType);
        generatedExamples.put(typeName, example);
        return example;
    }

    public String generateSimpleExample(String typeName) {
        if (typeName == null) return null;
        typeName = typeName.trim();

        switch (typeName) {
            case "String":
            case "string":
                return generateStringExample("default");
            case "Integer":
            case "int":
                return String.valueOf(RANDOM.nextInt(100) + 1);
            case "Long":
            case "long":
                return String.valueOf(RANDOM.nextLong(10000) + 1);
            case "Boolean":
            case "boolean":
                return String.valueOf(RANDOM.nextBoolean());
            case "Double":
            case "double":
            case "BigDecimal":
                return String.format("%.2f", RANDOM.nextDouble() * 1000);
            case "Float":
            case "float":
                return String.format("%.2f", RANDOM.nextFloat() * 100);
            case "Date":
            case "LocalDate":
                return LocalDate.now().format(DATE_FORMAT);
            case "LocalDateTime":
                return LocalDateTime.now().format(DATETIME_FORMAT);
            default:
                return null;
        }
    }

    private String generateStringExample(String fieldName) {
        String lowerName = fieldName.toLowerCase();
        if (lowerName.contains("name") || lowerName.contains("username")) {
            return "张三";
        } else if (lowerName.contains("email") || lowerName.contains("mail")) {
            return "example@test.com";
        } else if (lowerName.contains("phone") || lowerName.contains("mobile")) {
            return "13800138000";
        } else if (lowerName.contains("id")) {
            return "1001";
        } else if (lowerName.contains("url") || lowerName.contains("link")) {
            return "https://example.com";
        } else if (lowerName.contains("address")) {
            return "北京市朝阳区XX街道";
        } else if (lowerName.contains("status") || lowerName.contains("state")) {
            return "ACTIVE";
        } else if (lowerName.contains("type")) {
            return "NORMAL";
        } else if (lowerName.contains("code")) {
            return "200";
        } else if (lowerName.contains("msg") || lowerName.contains("message")) {
            return "操作成功";
        } else if (lowerName.contains("title")) {
            return "示例标题";
        } else if (lowerName.contains("desc") || lowerName.contains("description")) {
            return "这是一段示例描述内容";
        } else if (lowerName.contains("password")) {
            return "******";
        } else {
            return "示例内容";
        }
    }

    private Object parseExampleValue(String example, String type) {
        if (example == null) return null;
        switch (type) {
            case "Integer":
            case "int":
                try {
                    return Integer.parseInt(example);
                } catch (NumberFormatException e) {
                    return example;
                }
            case "Long":
            case "long":
                try {
                    return Long.parseLong(example);
                } catch (NumberFormatException e) {
                    return example;
                }
            case "Boolean":
            case "boolean":
                return Boolean.parseBoolean(example);
            case "Double":
            case "double":
                try {
                    return Double.parseDouble(example);
                } catch (NumberFormatException e) {
                    return example;
                }
            case "Float":
            case "float":
                try {
                    return Float.parseFloat(example);
                } catch (NumberFormatException e) {
                    return example;
                }
            case "BigDecimal":
                try {
                    return new BigDecimal(example);
                } catch (NumberFormatException e) {
                    return example;
                }
            default:
                return example;
        }
    }

    public Map<String, Object> generateRequestParams(Map<String, String[]> params) {
        Map<String, Object> result = new LinkedHashMap<>();
        if (params == null) return result;
        for (Map.Entry<String, String[]> entry : params.entrySet()) {
            String[] values = entry.getValue();
            if (values != null && values.length > 0) {
                result.put(entry.getKey(), values.length == 1 ? values[0] : values);
            }
        }
        return result;
    }
}
