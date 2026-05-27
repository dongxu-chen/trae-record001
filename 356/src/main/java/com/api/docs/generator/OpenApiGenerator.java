package com.api.docs.generator;

import com.api.docs.config.GeneratorConfig;
import com.api.docs.model.*;
import io.swagger.v3.core.util.Yaml;
import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.Operation;
import io.swagger.v3.oas.models.PathItem;
import io.swagger.v3.oas.models.Paths;
import io.swagger.v3.oas.models.info.Contact;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.info.License;
import io.swagger.v3.oas.models.media.*;
import io.swagger.v3.oas.models.parameters.Parameter;
import io.swagger.v3.oas.models.parameters.PathParameter;
import io.swagger.v3.oas.models.parameters.QueryParameter;
import io.swagger.v3.oas.models.parameters.RequestBody;
import io.swagger.v3.oas.models.responses.ApiResponse;
import io.swagger.v3.oas.models.responses.ApiResponses;
import io.swagger.v3.oas.models.servers.Server;
import io.swagger.v3.oas.models.tags.Tag;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.util.*;

public class OpenApiGenerator {
    private static final Logger logger = LoggerFactory.getLogger(OpenApiGenerator.class);
    private final GeneratorConfig config;

    public OpenApiGenerator(GeneratorConfig config) {
        this.config = config;
    }

    public OpenAPI generate(ApiInfo apiInfo) {
        logger.info("开始生成OpenAPI 3.0文档");

        OpenAPI openAPI = new OpenAPI();

        Info info = new Info();
        info.setTitle(apiInfo.getTitle());
        info.setDescription(apiInfo.getDescription());
        info.setVersion(apiInfo.getVersion());
        info.setContact(new Contact().name("API Generator"));
        info.setLicense(new License().name("Apache 2.0").url("https://www.apache.org/licenses/LICENSE-2.0"));
        openAPI.setInfo(info);

        List<Server> servers = new ArrayList<>();
        servers.add(new Server().url(apiInfo.getServerUrl()).description("Default server"));
        openAPI.setServers(servers);

        List<Tag> tags = new ArrayList<>();
        for (ControllerInfo controller : apiInfo.getControllers()) {
            Tag tag = new Tag();
            tag.setName(controller.getClassName());
            tag.setDescription(controller.getDescription());
            tags.add(tag);
        }
        openAPI.setTags(tags);

        Paths paths = new Paths();
        for (ControllerInfo controller : apiInfo.getControllers()) {
            for (MethodInfo method : controller.getMethods()) {
                String path = method.getPath();
                if (path == null || path.isEmpty()) {
                    path = "/";
                }
                PathItem pathItem = paths.get(path);
                if (pathItem == null) {
                    pathItem = new PathItem();
                    paths.put(path, pathItem);
                }
                Operation operation = buildOperation(method);
                setPathItemOperation(pathItem, method.getHttpMethod(), operation);
            }
        }
        openAPI.setPaths(paths);

        Map<String, Schema> schemas = new HashMap<>();
        for (ModelInfo model : apiInfo.getModels()) {
            schemas.put(model.getClassName(), buildSchema(model));
        }
        openAPI.components(new io.swagger.v3.oas.models.Components().schemas(schemas));

        logger.info("OpenAPI文档生成完成: {} 个端点, {} 个模型",
                paths.size(), schemas.size());
        return openAPI;
    }

    private void setPathItemOperation(PathItem pathItem, String httpMethod, Operation operation) {
        if (httpMethod == null) {
            httpMethod = "GET";
        }
        switch (httpMethod.toUpperCase()) {
            case "GET":
                pathItem.setGet(operation);
                break;
            case "POST":
                pathItem.setPost(operation);
                break;
            case "PUT":
                pathItem.setPut(operation);
                break;
            case "DELETE":
                pathItem.setDelete(operation);
                break;
            case "PATCH":
                pathItem.setPatch(operation);
                break;
            case "HEAD":
                pathItem.setHead(operation);
                break;
            case "OPTIONS":
                pathItem.setOptions(operation);
                break;
            default:
                pathItem.setGet(operation);
        }
    }

    private Operation buildOperation(MethodInfo methodInfo) {
        Operation operation = new Operation();
        operation.setSummary(methodInfo.getSummary());
        operation.setDescription(methodInfo.getDescription());
        operation.setDeprecated(methodInfo.isDeprecated());
        operation.setTags(methodInfo.getTags());
        operation.setOperationId(methodInfo.getName());

        List<Parameter> parameters = new ArrayList<>();
        for (ParameterInfo paramInfo : methodInfo.getParameters()) {
            Parameter param = buildParameter(paramInfo);
            if (param != null) {
                parameters.add(param);
            }
        }
        operation.setParameters(parameters);

        if (methodInfo.getRequestBodyType() != null && !methodInfo.getRequestBodyType().isEmpty()) {
            RequestBody requestBody = new RequestBody();
            requestBody.setRequired(true);
            requestBody.setDescription("Request body");
            Content content = new Content();
            MediaType mediaType = new MediaType();
            mediaType.setSchema(new Schema<>().$ref(cleanRefType(methodInfo.getRequestBodyType())));
            content.addMediaType("application/json", mediaType);
            requestBody.setContent(content);
            operation.setRequestBody(requestBody);
        }

        ApiResponses responses = new ApiResponses();
        ApiResponse successResponse = new ApiResponse();
        successResponse.setDescription("Successful operation");
        if (methodInfo.getResponseType() != null && !methodInfo.getResponseType().isEmpty()
                && !methodInfo.getResponseType().equals("void") && !methodInfo.getResponseType().equals("Void")) {
            Content content = new Content();
            MediaType mediaType = new MediaType();
            String refType = cleanRefType(methodInfo.getResponseType());
            if (refType != null && !refType.isEmpty()) {
                mediaType.setSchema(new Schema<>().$ref(refType));
            } else {
                mediaType.setSchema(new StringSchema());
            }
            content.addMediaType("application/json", mediaType);
            successResponse.setContent(content);
        }
        responses.addApiResponse("200", successResponse);

        ApiResponse errorResponse = new ApiResponse();
        errorResponse.setDescription("Error response");
        responses.addApiResponse("default", errorResponse);

        operation.setResponses(responses);

        return operation;
    }

    private Parameter buildParameter(ParameterInfo paramInfo) {
        Parameter parameter;
        String in = paramInfo.getIn();
        if ("path".equals(in)) {
            parameter = new PathParameter();
        } else if ("query".equals(in)) {
            parameter = new QueryParameter();
        } else {
            parameter = new Parameter();
            parameter.setIn(in);
        }

        parameter.setName(paramInfo.getName());
        parameter.setDescription(paramInfo.getDescription());
        parameter.setRequired(paramInfo.isRequired());
        parameter.setSchema(mapToSchema(paramInfo.getType()));

        return parameter;
    }

    private Schema buildSchema(ModelInfo modelInfo) {
        Schema schema = new Schema();
        schema.setType("object");
        schema.setTitle(modelInfo.getClassName());
        schema.setDescription(modelInfo.getDescription());

        Map<String, Schema> properties = new LinkedHashMap<>();
        List<String> requiredFields = new ArrayList<>();

        for (FieldInfo fieldInfo : modelInfo.getFields()) {
            Schema fieldSchema = mapToSchema(fieldInfo.getType());
            fieldSchema.setDescription(fieldInfo.getDescription());
            if (fieldInfo.getExample() != null && !fieldInfo.getExample().isEmpty()) {
                fieldSchema.setExample(fieldInfo.getExample());
            }
            fieldSchema.setDeprecated(fieldInfo.isDeprecated());
            properties.put(fieldInfo.getName(), fieldSchema);

            if (fieldInfo.isRequired()) {
                requiredFields.add(fieldInfo.getName());
            }
        }

        schema.setProperties(properties);
        if (!requiredFields.isEmpty()) {
            schema.setRequired(requiredFields);
        }

        return schema;
    }

    private Schema mapToSchema(String typeName) {
        if (typeName == null) {
            return new StringSchema();
        }
        typeName = typeName.trim();

        if (typeName.endsWith("[]")) {
            ArraySchema arraySchema = new ArraySchema();
            arraySchema.setItems(mapToSchema(typeName.substring(0, typeName.length() - 2)));
            return arraySchema;
        }

        int genericStart = typeName.indexOf('<');
        int genericEnd = typeName.lastIndexOf('>');

        if (genericStart > 0 && genericEnd > genericStart) {
            String outerType = typeName.substring(0, genericStart).trim();
            String genericContent = typeName.substring(genericStart + 1, genericEnd);
            List<String> genericParams = splitGenericParameters(genericContent);

            if (isCollectionType(outerType)) {
                ArraySchema arraySchema = new ArraySchema();
                if (!genericParams.isEmpty()) {
                    arraySchema.setItems(mapToSchema(genericParams.get(0)));
                } else {
                    arraySchema.setItems(new StringSchema());
                }
                return arraySchema;
            } else if (isMapType(outerType)) {
                MapSchema mapSchema = new MapSchema();
                if (genericParams.size() >= 2) {
                    mapSchema.setAdditionalProperties(mapToSchema(genericParams.get(1)));
                } else {
                    mapSchema.setAdditionalProperties(new StringSchema());
                }
                return mapSchema;
            } else if (isPageType(outerType)) {
                return buildPageSchema(genericParams);
            } else {
                Schema genericSchema = new Schema();
                genericSchema.setType("object");
                genericSchema.setTitle(outerType);
                Map<String, Schema> properties = new LinkedHashMap<>();
                for (int i = 0; i < genericParams.size(); i++) {
                    properties.put("genericType" + (i + 1), mapToSchema(genericParams.get(i)));
                }
                genericSchema.setProperties(properties);
                return genericSchema;
            }
        }

        switch (typeName) {
            case "String":
                return new StringSchema();
            case "Integer":
            case "int":
            case "Long":
            case "long":
            case "Short":
            case "short":
                return new IntegerSchema();
            case "Boolean":
            case "boolean":
                return new BooleanSchema();
            case "Double":
            case "double":
            case "Float":
            case "float":
                return new NumberSchema();
            case "Date":
            case "LocalDate":
                DateSchema dateSchema = new DateSchema();
                dateSchema.setFormat("date");
                return dateSchema;
            case "LocalDateTime":
                DateTimeSchema dateTimeSchema = new DateTimeSchema();
                dateTimeSchema.setFormat("date-time");
                return dateTimeSchema;
            case "BigDecimal":
                NumberSchema decimalSchema = new NumberSchema();
                decimalSchema.setFormat("double");
                return decimalSchema;
            case "void":
            case "Void":
                return null;
            default:
                if (typeName.startsWith("java.") || typeName.startsWith("javax.")) {
                    return new StringSchema();
                }
                return new Schema<>().$ref("#/components/schemas/" + typeName);
        }
    }

    private List<String> splitGenericParameters(String content) {
        List<String> params = new ArrayList<>();
        int depth = 0;
        StringBuilder current = new StringBuilder();

        for (char c : content.toCharArray()) {
            if (c == '<') {
                depth++;
                current.append(c);
            } else if (c == '>') {
                depth--;
                current.append(c);
            } else if (c == ',' && depth == 0) {
                params.add(current.toString().trim());
                current = new StringBuilder();
            } else {
                current.append(c);
            }
        }

        if (current.length() > 0) {
            params.add(current.toString().trim());
        }

        return params;
    }

    private boolean isCollectionType(String type) {
        return type.equals("List") || type.equals("Set") || type.equals("Collection")
                || type.equals("ArrayList") || type.equals("HashSet") || type.equals("LinkedList")
                || type.equals("Vector") || type.equals("TreeSet") || type.endsWith("List");
    }

    private boolean isMapType(String type) {
        return type.equals("Map") || type.equals("HashMap") || type.equals("LinkedHashMap")
                || type.equals("TreeMap") || type.equals("ConcurrentHashMap");
    }

    private boolean isPageType(String type) {
        return type.equals("Page") || type.equals("IPage") || type.equals("PageResult")
                || type.endsWith("Page") || type.endsWith("PageResponse");
    }

    private Schema buildPageSchema(List<String> genericParams) {
        ObjectSchema pageSchema = new ObjectSchema();
        pageSchema.setTitle("Page");
        Map<String, Schema> properties = new LinkedHashMap<>();

        properties.put("total", new LongSchema().description("总记录数"));
        properties.put("size", new IntegerSchema().description("每页大小"));
        properties.put("current", new IntegerSchema().description("当前页码"));
        properties.put("pages", new IntegerSchema().description("总页数"));

        ArraySchema recordsSchema = new ArraySchema();
        if (!genericParams.isEmpty()) {
            recordsSchema.setItems(mapToSchema(genericParams.get(0)));
        } else {
            recordsSchema.setItems(new ObjectSchema());
        }
        recordsSchema.setDescription("数据列表");
        properties.put("records", recordsSchema);

        pageSchema.setProperties(properties);
        return pageSchema;
    }

    private String cleanRefType(String typeName) {
        String firstType = extractFirstNonPrimitiveType(typeName);
        if (firstType == null || firstType.isEmpty()) {
            return "";
        }
        if (firstType.startsWith("java.") || isPrimitiveType(firstType)) {
            return "";
        }
        return "#/components/schemas/" + firstType;
    }

    private String extractFirstNonPrimitiveType(String typeName) {
        if (typeName == null) return null;
        typeName = typeName.trim();

        int genericStart = typeName.indexOf('<');
        int genericEnd = typeName.lastIndexOf('>');

        if (genericStart > 0 && genericEnd > genericStart) {
            String outerType = typeName.substring(0, genericStart).trim();
            if (!isCollectionType(outerType) && !isMapType(outerType) && !isPageType(outerType)
                    && !isPrimitiveType(outerType) && !outerType.startsWith("java.")) {
                return outerType;
            }
            String genericContent = typeName.substring(genericStart + 1, genericEnd);
            List<String> genericParams = splitGenericParameters(genericContent);
            for (String param : genericParams) {
                String result = extractFirstNonPrimitiveType(param);
                if (result != null && !result.isEmpty()) {
                    return result;
                }
            }
            return null;
        }

        return typeName;
    }

    private boolean isPrimitiveType(String type) {
        return type.equals("String") || type.equals("Integer") || type.equals("int")
                || type.equals("Long") || type.equals("long") || type.equals("Boolean")
                || type.equals("boolean") || type.equals("Double") || type.equals("double")
                || type.equals("Float") || type.equals("float") || type.equals("Short")
                || type.equals("short") || type.equals("Byte") || type.equals("byte")
                || type.equals("Character") || type.equals("char") || type.equals("void")
                || type.equals("Void") || type.equals("Date") || type.equals("LocalDate")
                || type.equals("LocalDateTime") || type.equals("BigDecimal") || type.equals("Object");
    }

    public void writeOpenAPI(OpenAPI openAPI, String outputPath, String format) throws IOException {
        File outputDir = new File(outputPath);
        if (!outputDir.exists()) {
            outputDir.mkdirs();
        }

        String fileName;
        String content;

        if ("yaml".equalsIgnoreCase(format) || "yml".equalsIgnoreCase(format)) {
            fileName = "openapi.yaml";
            content = Yaml.pretty().writeValueAsString(openAPI);
        } else {
            fileName = "openapi.json";
            content = io.swagger.v3.core.util.Json.pretty().writeValueAsString(openAPI);
        }

        File outputFile = new File(outputDir, fileName);
        try (FileWriter writer = new FileWriter(outputFile)) {
            writer.write(content);
        }

        logger.info("OpenAPI文档已写入: {}", outputFile.getAbsolutePath());
    }
}