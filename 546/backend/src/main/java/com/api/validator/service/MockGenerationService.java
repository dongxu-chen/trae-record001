package com.api.validator.service;

import com.api.validator.model.MockGenerationResult;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.*;

@Service
public class MockGenerationService {

    private final ObjectMapper objectMapper = new ObjectMapper();
    private final Random random = new Random();

    private static final Map<String, String[]> FORMAT_MOCKS = new HashMap<>();

    static {
        FORMAT_MOCKS.put("email", new String[]{"user@example.com", "admin@test.org", "dev@company.io"});
        FORMAT_MOCKS.put("date-time", new String[]{"2025-01-15T10:30:00Z", "2025-06-20T14:00:00Z"});
        FORMAT_MOCKS.put("date", new String[]{"2025-01-15", "2025-06-20"});
        FORMAT_MOCKS.put("time", new String[]{"10:30:00", "14:00:00"});
        FORMAT_MOCKS.put("uri", new String[]{"https://example.com/resource/1", "https://api.test.org/v2/items"});
        FORMAT_MOCKS.put("url", new String[]{"https://example.com/resource/1", "https://api.test.org/v2/items"});
        FORMAT_MOCKS.put("uuid", new String[]{"550e8400-e29b-41d4-a716-446655440000", "6fa459ea-ee8a-3ca4-894e-db77e160355e"});
        FORMAT_MOCKS.put("ipv4", new String[]{"192.168.1.1", "10.0.0.1"});
        FORMAT_MOCKS.put("ipv6", new String[]{"::1", "2001:0db8:85a3:0000:0000:8a2e:0370:7334"});
        FORMAT_MOCKS.put("hostname", new String[]{"api.example.com", "web-server-01"});
        FORMAT_MOCKS.put("password", new String[]{"********", "P@ssw0rd!"});
    }

    private static final Map<String, String[]> FIELD_NAME_MOCKS = new HashMap<>();

    static {
        FIELD_NAME_MOCKS.put("id", new String[]{"1", "100", "42"});
        FIELD_NAME_MOCKS.put("name", new String[]{"示例名称", "测试项目", "Mock Data"});
        FIELD_NAME_MOCKS.put("username", new String[]{"zhangsan", "user_01", "admin"});
        FIELD_NAME_MOCKS.put("email", new String[]{"user@example.com", "test@mail.com"});
        FIELD_NAME_MOCKS.put("phone", new String[]{"13800138000", "18612345678"});
        FIELD_NAME_MOCKS.put("address", new String[]{"北京市朝阳区xx路xx号", "上海市浦东新区xx街xx号"});
        FIELD_NAME_MOCKS.put("city", new String[]{"北京", "上海", "深圳"});
        FIELD_NAME_MOCKS.put("country", new String[]{"中国", "美国"});
        FIELD_NAME_MOCKS.put("title", new String[]{"标题示例", "测试标题"});
        FIELD_NAME_MOCKS.put("description", new String[]{"这是一段描述文字", "示例描述信息"});
        FIELD_NAME_MOCKS.put("status", new String[]{"active", "inactive", "pending"});
        FIELD_NAME_MOCKS.put("type", new String[]{"standard", "premium"});
        FIELD_NAME_MOCKS.put("code", new String[]{"200", "ERR_001", "CODE_42"});
        FIELD_NAME_MOCKS.put("message", new String[]{"操作成功", "请求已处理"});
        FIELD_NAME_MOCKS.put("url", new String[]{"https://example.com/resource/1"});
        FIELD_NAME_MOCKS.put("avatar", new String[]{"https://example.com/avatars/default.png"});
        FIELD_NAME_MOCKS.put("image", new String[]{"https://example.com/images/sample.jpg"});
        FIELD_NAME_MOCKS.put("price", new String[]{"99.99", "199.00", "0.01"});
        FIELD_NAME_MOCKS.put("amount", new String[]{"100", "500", "1000"});
        FIELD_NAME_MOCKS.put("total", new String[]{"399.96", "1999.00"});
        FIELD_NAME_MOCKS.put("age", new String[]{"25", "30", "18"});
        FIELD_NAME_MOCKS.put("count", new String[]{"10", "50", "100"});
        FIELD_NAME_MOCKS.put("page", new String[]{"1", "2", "5"});
        FIELD_NAME_MOCKS.put("size", new String[]{"20", "50", "100"});
        FIELD_NAME_MOCKS.put("created_at", new String[]{"2025-01-15T10:30:00Z"});
        FIELD_NAME_MOCKS.put("updated_at", new String[]{"2025-06-20T14:00:00Z"});
        FIELD_NAME_MOCKS.put("created_by", new String[]{"system", "admin"});
        FIELD_NAME_MOCKS.put("version", new String[]{"1.0.0", "2.1.3"});
    }

    public MockGenerationResult generateMock(JsonNode jsonSchema, String path, String method, Integer statusCode) {
        MockGenerationResult result = new MockGenerationResult();
        result.setPath(path);
        result.setMethod(method);
        result.setStatusCode(statusCode);

        try {
            JsonNode mockNode = generateMockFromSchema(jsonSchema, "", result);
            result.setMockResponse(objectMapper.writerWithDefaultPrettyPrinter().writeValueAsString(mockNode));
            result.setGenerated(true);
        } catch (Exception e) {
            result.setGenerated(false);
            result.addNote("Mock生成失败: " + e.getMessage());
        }

        return result;
    }

    private JsonNode generateMockFromSchema(JsonNode schema, String fieldName, MockGenerationResult result) {
        if (schema == null) {
            return objectMapper.getNodeFactory().textNode("null");
        }

        if (schema.has("example")) {
            return objectMapper.valueToTree(schema.get("example"));
        }

        if (schema.has("enum") && schema.get("enum").isArray() && schema.get("enum").size() > 0) {
            int index = random.nextInt(schema.get("enum").size());
            return schema.get("enum").get(index);
        }

        if (schema.has("default")) {
            return schema.get("default");
        }

        String type = schema.has("type") ? schema.get("type").asText() : "object";

        switch (type) {
            case "object":
                return generateObjectMock(schema, fieldName, result);
            case "array":
                return generateArrayMock(schema, fieldName, result);
            case "string":
                return generateStringMock(schema, fieldName, result);
            case "integer":
                return generateIntegerMock(schema, fieldName);
            case "number":
                return generateNumberMock(schema, fieldName);
            case "boolean":
                return generateBooleanMock(schema, fieldName);
            default:
                return objectMapper.getNodeFactory().textNode("unknown");
        }
    }

    private ObjectNode generateObjectMock(JsonNode schema, String parentName, MockGenerationResult result) {
        ObjectNode mockNode = objectMapper.createObjectNode();

        if (schema.has("properties")) {
            JsonNode properties = schema.get("properties");
            Iterator<Map.Entry<String, JsonNode>> fields = properties.fields();

            while (fields.hasNext()) {
                Map.Entry<String, JsonNode> entry = fields.next();
                String propName = entry.getKey();
                JsonNode propSchema = entry.getValue();

                JsonNode propMock = generateMockFromSchema(propSchema, propName, result);
                mockNode.set(propName, propMock);
            }
        }

        if (!schema.has("properties") && !schema.has("additionalProperties")) {
            result.addNote("对象字段 '" + parentName + "' 缺少properties定义，生成空对象");
        }

        return mockNode;
    }

    private ArrayNode generateArrayMock(JsonNode schema, String fieldName, MockGenerationResult result) {
        ArrayNode mockArray = objectMapper.createArrayNode();

        int minItems = schema.has("minItems") ? schema.get("minItems").asInt() : 1;
        int maxItems = schema.has("maxItems") ? schema.get("maxItems").asInt() : Math.max(minItems + 1, 3);
        int itemCount = Math.min(minItems + random.nextInt(Math.max(maxItems - minItems, 1)) + 1, maxItems);
        itemCount = Math.max(itemCount, 1);

        if (schema.has("items")) {
            JsonNode itemSchema = schema.get("items");
            for (int i = 0; i < itemCount; i++) {
                JsonNode itemMock = generateMockFromSchema(itemSchema, fieldName + "[" + i + "]", result);
                mockArray.add(itemMock);
            }
        } else {
            result.addNote("数组字段 '" + fieldName + "' 缺少items定义，生成空数组");
        }

        return mockArray;
    }

    private JsonNode generateStringMock(JsonNode schema, String fieldName, MockGenerationResult result) {
        if (schema.has("format")) {
            String format = schema.get("format").asText();
            return generateFormatMock(format, fieldName);
        }

        if (FIELD_NAME_MOCKS.containsKey(fieldName)) {
            String[] mocks = FIELD_NAME_MOCKS.get(fieldName);
            return objectMapper.getNodeFactory().textNode(mocks[random.nextInt(mocks.length)]);
        }

        if (schema.has("pattern")) {
            String pattern = schema.get("pattern").asText();
            String generated = generateFromPattern(pattern);
            if (generated != null) {
                return objectMapper.getNodeFactory().textNode(generated);
            }
            result.addNote("字段 '" + fieldName + "' 的正则模式 '" + pattern + "' 无法自动生成，使用默认值");
        }

        int minLength = schema.has("minLength") ? schema.get("minLength").asInt() : 0;
        int maxLength = schema.has("maxLength") ? schema.get("maxLength").asInt() : 20;

        int length = Math.max(minLength, Math.min(5, maxLength));
        String value = generateRandomString(length);
        return objectMapper.getNodeFactory().textNode(value);
    }

    private JsonNode generateFormatMock(String format, String fieldName) {
        if (FIELD_NAME_MOCKS.containsKey(fieldName)) {
            String[] mocks = FIELD_NAME_MOCKS.get(fieldName);
            return objectMapper.getNodeFactory().textNode(mocks[random.nextInt(mocks.length)]);
        }

        if (FORMAT_MOCKS.containsKey(format)) {
            String[] mocks = FORMAT_MOCKS.get(format);
            return objectMapper.getNodeFactory().textNode(mocks[random.nextInt(mocks.length)]);
        }

        return switch (format) {
            case "int32" -> objectMapper.getNodeFactory().numberNode(random.nextInt(100000));
            case "int64" -> objectMapper.getNodeFactory().numberNode(random.nextLong(1000000000L));
            case "float" -> objectMapper.getNodeFactory().numberNode(random.nextFloat() * 100);
            case "double" -> objectMapper.getNodeFactory().numberNode(random.nextDouble() * 1000);
            case "byte" -> objectMapper.getNodeFactory().textNode("SGVsbG8gV29ybGQ=");
            case "binary" -> objectMapper.getNodeFactory().textNode("<binary-data>");
            default -> objectMapper.getNodeFactory().textNode("mock_" + format);
        };
    }

    private JsonNode generateIntegerMock(JsonNode schema, String fieldName) {
        if (FIELD_NAME_MOCKS.containsKey(fieldName)) {
            try {
                String[] mocks = FIELD_NAME_MOCKS.get(fieldName);
                return objectMapper.getNodeFactory().numberNode(Integer.parseInt(mocks[random.nextInt(mocks.length)]));
            } catch (NumberFormatException ignored) {
            }
        }

        long minimum = schema.has("minimum") ? schema.get("minimum").asLong() : 1;
        long maximum = schema.has("maximum") ? schema.get("maximum").asLong() : 1000;

        if (schema.has("exclusiveMinimum") && schema.get("exclusiveMinimum").asBoolean()) {
            minimum++;
        }
        if (schema.has("exclusiveMaximum") && schema.get("exclusiveMaximum").asBoolean()) {
            maximum--;
        }

        if (schema.has("multipleOf")) {
            long multipleOf = schema.get("multipleOf").asLong();
            if (multipleOf > 0) {
                long base = (minimum / multipleOf) * multipleOf;
                return objectMapper.getNodeFactory().numberNode(base + multipleOf);
            }
        }

        long value = minimum + (Math.abs(random.nextLong()) % (maximum - minimum + 1));
        return objectMapper.getNodeFactory().numberNode(value);
    }

    private JsonNode generateNumberMock(JsonNode schema, String fieldName) {
        if (FIELD_NAME_MOCKS.containsKey(fieldName)) {
            try {
                String[] mocks = FIELD_NAME_MOCKS.get(fieldName);
                return objectMapper.getNodeFactory().numberNode(new BigDecimal(mocks[random.nextInt(mocks.length)]));
            } catch (NumberFormatException ignored) {
            }
        }

        double minimum = schema.has("minimum") ? schema.get("minimum").asDouble() : 0.0;
        double maximum = schema.has("maximum") ? schema.get("maximum").asDouble() : 1000.0;

        double value = minimum + (random.nextDouble() * (maximum - minimum));
        BigDecimal bd = BigDecimal.valueOf(value).setScale(2, RoundingMode.HALF_UP);
        return objectMapper.getNodeFactory().numberNode(bd);
    }

    private JsonNode generateBooleanMock(JsonNode schema, String fieldName) {
        return objectMapper.getNodeFactory().booleanNode(random.nextBoolean());
    }

    private String generateRandomString(int length) {
        String chars = "abcdefghijklmnopqrstuvwxyz0123456789";
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < length; i++) {
            sb.append(chars.charAt(random.nextInt(chars.length())));
        }
        return "mock_" + sb;
    }

    private String generateFromPattern(String pattern) {
        try {
            String simplified = pattern;
            simplified = simplified.replace("\\d", "0");
            simplified = simplified.replace("[0-9]", "0");
            simplified = simplified.replace("\\w", "a");
            simplified = simplified.replace(".", "x");
            simplified = simplified.replace("^", "");
            simplified = simplified.replace("$", "");

            if (simplified.matches("^[0ax\\-:T.Z]+$")) {
                return simplified;
            }
        } catch (Exception ignored) {
        }
        return null;
    }
}
