package com.api.validator.service;

import com.api.validator.model.ValidationResult;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.Operation;
import io.swagger.v3.oas.models.PathItem;
import io.swagger.v3.oas.models.media.Schema;
import io.swagger.v3.oas.models.responses.ApiResponse;
import io.swagger.v3.parser.OpenAPIV3Parser;
import io.swagger.v3.parser.core.models.ParseOptions;
import io.swagger.v3.parser.core.models.SwaggerParseResult;
import org.springframework.stereotype.Service;

import java.util.*;

@Service
public class OpenApiParserService {

    private final ObjectMapper objectMapper = new ObjectMapper();

    public OpenAPI parseOpenApiSpec(String openApiContent) {
        ParseOptions options = new ParseOptions();
        options.setResolve(true);
        options.setResolveFully(true);
        
        SwaggerParseResult result = new OpenAPIV3Parser().readContents(openApiContent, null, options);
        
        if (result.getMessages() != null && !result.getMessages().isEmpty()) {
            throw new IllegalArgumentException("OpenAPI解析错误: " + String.join(", ", result.getMessages()));
        }
        
        return result.getOpenAPI();
    }

    public Schema<?> extractResponseSchema(OpenAPI openAPI, String path, String method, Integer statusCode) {
        PathItem pathItem = openAPI.getPaths().get(path);
        if (pathItem == null) {
            throw new IllegalArgumentException("路径未找到: " + path);
        }

        Operation operation = getOperationByMethod(pathItem, method.toUpperCase());
        if (operation == null) {
            throw new IllegalArgumentException("方法未找到: " + method);
        }

        String statusCodeStr = statusCode != null ? statusCode.toString() : "200";
        ApiResponse response = operation.getResponses().get(statusCodeStr);
        
        if (response == null) {
            response = operation.getResponses().get("default");
        }
        
        if (response == null || response.getContent() == null) {
            throw new IllegalArgumentException("响应定义未找到，状态码: " + statusCodeStr);
        }

        var contentEntry = response.getContent().entrySet().stream()
                .filter(e -> e.getKey().contains("application/json"))
                .findFirst();
        
        if (contentEntry.isEmpty()) {
            throw new IllegalArgumentException("未找到JSON响应内容定义");
        }

        return contentEntry.get().getSchema();
    }

    public JsonNode convertSchemaToJsonSchema(Schema<?> schema, OpenAPI openAPI) {
        Map<String, Object> jsonSchemaMap = new LinkedHashMap<>();
        jsonSchemaMap.put("$schema", "http://json-schema.org/draft-07/schema#");
        
        buildJsonSchema(schema, jsonSchemaMap, new HashSet<>());
        
        return objectMapper.valueToTree(jsonSchemaMap);
    }

    @SuppressWarnings("unchecked")
    private void buildJsonSchema(Schema<?> schema, Map<String, Object> jsonSchemaMap, Set<String> processedSchemas) {
        if (schema == null) {
            return;
        }

        String schemaName = schema.getName();
        if (schemaName != null && processedSchemas.contains(schemaName)) {
            return;
        }
        if (schemaName != null) {
            processedSchemas.add(schemaName);
        }

        String type = getJsonSchemaType(schema.getType());
        if (type != null) {
            jsonSchemaMap.put("type", type);
        }

        if (schema.getDescription() != null) {
            jsonSchemaMap.put("description", schema.getDescription());
        }

        if (schema.getEnum() != null && !schema.getEnum().isEmpty()) {
            jsonSchemaMap.put("enum", schema.getEnum());
        }

        if ("object".equals(type) && schema.getProperties() != null) {
            Map<String, Object> properties = new LinkedHashMap<>();
            List<String> requiredFields = new ArrayList<>();

            for (Map.Entry<String, Schema> entry : ((Map<String, Schema>) schema.getProperties()).entrySet()) {
                String propName = entry.getKey();
                Schema<?> propSchema = entry.getValue();
                
                Map<String, Object> propJsonSchema = new LinkedHashMap<>();
                buildJsonSchema(propSchema, propJsonSchema, processedSchemas);
                properties.put(propName, propJsonSchema);

                if (Boolean.TRUE.equals(propSchema.getNullable()) == false) {
                    if (schema.getRequired() != null && schema.getRequired().contains(propName)) {
                        requiredFields.add(propName);
                    }
                }
            }

            jsonSchemaMap.put("properties", properties);
            if (!requiredFields.isEmpty()) {
                jsonSchemaMap.put("required", requiredFields);
            }
        }

        if ("array".equals(type) && schema.getItems() != null) {
            Map<String, Object> itemsSchema = new LinkedHashMap<>();
            buildJsonSchema(schema.getItems(), itemsSchema, processedSchemas);
            jsonSchemaMap.put("items", itemsSchema);
        }

        if (type == null || "string".equals(type)) {
            if (schema.getFormat() != null) {
                jsonSchemaMap.put("format", schema.getFormat());
            }
        }

        if (schema.getExample() != null) {
            jsonSchemaMap.put("example", schema.getExample());
        }
    }

    private String getJsonSchemaType(String openApiType) {
        if (openApiType == null) {
            return null;
        }
        return switch (openApiType) {
            case "integer" -> "integer";
            case "number" -> "number";
            case "string" -> "string";
            case "boolean" -> "boolean";
            case "array" -> "array";
            case "object" -> "object";
            default -> openApiType;
        };
    }

    private Operation getOperationByMethod(PathItem pathItem, String method) {
        return switch (method) {
            case "GET" -> pathItem.getGet();
            case "POST" -> pathItem.getPost();
            case "PUT" -> pathItem.getPut();
            case "DELETE" -> pathItem.getDelete();
            case "PATCH" -> pathItem.getPatch();
            case "HEAD" -> pathItem.getHead();
            case "OPTIONS" -> pathItem.getOptions();
            case "TRACE" -> pathItem.getTrace();
            default -> null;
        };
    }

    public List<Map<String, String>> extractAllEndpoints(OpenAPI openAPI) {
        List<Map<String, String>> endpoints = new ArrayList<>();
        
        for (Map.Entry<String, PathItem> pathEntry : openAPI.getPaths().entrySet()) {
            String path = pathEntry.getKey();
            PathItem pathItem = pathEntry.getValue();
            
            addEndpointIfPresent(endpoints, path, "GET", pathItem.getGet());
            addEndpointIfPresent(endpoints, path, "POST", pathItem.getPost());
            addEndpointIfPresent(endpoints, path, "PUT", pathItem.getPut());
            addEndpointIfPresent(endpoints, path, "DELETE", pathItem.getDelete());
            addEndpointIfPresent(endpoints, path, "PATCH", pathItem.getPatch());
        }
        
        return endpoints;
    }

    private void addEndpointIfPresent(List<Map<String, String>> endpoints, String path, String method, Operation operation) {
        if (operation != null) {
            Map<String, String> endpoint = new LinkedHashMap<>();
            endpoint.put("path", path);
            endpoint.put("method", method);
            endpoint.put("summary", operation.getSummary() != null ? operation.getSummary() : "");
            endpoints.add(endpoint);
        }
    }
}
