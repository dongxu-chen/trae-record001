package com.api.docs.filter;

import com.api.docs.model.*;
import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.Operation;
import io.swagger.v3.oas.models.PathItem;
import io.swagger.v3.oas.models.Paths;
import io.swagger.v3.oas.models.tags.Tag;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.stream.Collectors;

public class PermissionFilter {
    private static final Logger logger = LoggerFactory.getLogger(PermissionFilter.class);

    public static class Role {
        public static final String ADMIN = "ADMIN";
        public static final String USER = "USER";
        public static final String GUEST = "GUEST";
        public static final String DEVELOPER = "DEVELOPER";
    }

    private final Set<String> allowedRoles;
    private final Set<String> sensitiveTags;
    private final Set<String> sensitivePaths;
    private final Set<String> sensitiveMethods;
    private final boolean hideInternalModels;

    private static final Set<String> DEFAULT_SENSITIVE_TAGS = new HashSet<>(Arrays.asList(
            "AdminController", "SystemController", "ConfigController", "MonitorController"
    ));

    private static final Set<String> DEFAULT_SENSITIVE_PATHS = new HashSet<>(Arrays.asList(
            "/api/admin", "/api/system", "/api/config", "/api/monitor", "/api/internal"
    ));

    private static final Set<String> INTERNAL_MODEL_SUFFIXES = new HashSet<>(Arrays.asList(
            "Internal", "Admin", "System", "Secret", "Config"
    ));

    public PermissionFilter() {
        this(Collections.singleton(Role.DEVELOPER));
    }

    public PermissionFilter(Set<String> allowedRoles) {
        this.allowedRoles = new HashSet<>(allowedRoles);
        this.sensitiveTags = new HashSet<>(DEFAULT_SENSITIVE_TAGS);
        this.sensitivePaths = new HashSet<>(DEFAULT_SENSITIVE_PATHS);
        this.sensitiveMethods = new HashSet<>();
        this.hideInternalModels = true;
    }

    public PermissionFilter(Set<String> allowedRoles, Set<String> sensitiveTags,
                            Set<String> sensitivePaths, Set<String> sensitiveMethods,
                            boolean hideInternalModels) {
        this.allowedRoles = new HashSet<>(allowedRoles);
        this.sensitiveTags = sensitiveTags != null ? new HashSet<>(sensitiveTags) : new HashSet<>();
        this.sensitivePaths = sensitivePaths != null ? new HashSet<>(sensitivePaths) : new HashSet<>();
        this.sensitiveMethods = sensitiveMethods != null ? new HashSet<>(sensitiveMethods) : new HashSet<>();
        this.hideInternalModels = hideInternalModels;
    }

    public void addSensitiveTag(String tag) {
        sensitiveTags.add(tag);
    }

    public void addSensitivePath(String path) {
        sensitivePaths.add(path);
    }

    public void addSensitiveMethod(String method) {
        sensitiveMethods.add(method);
    }

    public boolean isAdmin() {
        return allowedRoles.contains(Role.ADMIN);
    }

    public boolean isDeveloper() {
        return allowedRoles.contains(Role.DEVELOPER) || isAdmin();
    }

    public ApiInfo filterApiInfo(ApiInfo apiInfo) {
        if (isDeveloper()) {
            logger.debug("开发者角色，跳过权限过滤");
            return apiInfo;
        }

        logger.info("应用权限过滤，角色: {}", allowedRoles);

        ApiInfo filtered = new ApiInfo();
        filtered.setTitle(apiInfo.getTitle());
        filtered.setDescription(apiInfo.getDescription() + " (权限过滤后)");
        filtered.setVersion(apiInfo.getVersion());
        filtered.setServerUrl(apiInfo.getServerUrl());

        Set<String> referencedModels = new HashSet<>();

        for (ControllerInfo controller : apiInfo.getControllers()) {
            if (isSensitiveController(controller)) {
                logger.debug("隐藏敏感Controller: {}", controller.getClassName());
                continue;
            }

            ControllerInfo filteredController = new ControllerInfo();
            filteredController.setClassName(controller.getClassName());
            filteredController.setPackageName(controller.getPackageName());
            filteredController.setBasePath(controller.getBasePath());
            filteredController.setDescription(controller.getDescription());

            for (MethodInfo method : controller.getMethods()) {
                if (!isSensitiveMethod(method, controller.getBasePath())) {
                    filteredController.addMethod(method);
                    collectReferencedModels(method, referencedModels);
                } else {
                    logger.debug("隐藏敏感接口: {} {}", method.getHttpMethod(), method.getPath());
                }
            }

            if (!filteredController.getMethods().isEmpty()) {
                filtered.addController(filteredController);
            }
        }

        for (ModelInfo model : apiInfo.getModels()) {
            if (hideInternalModels && isInternalModel(model.getClassName())) {
                logger.debug("隐藏内部Model: {}", model.getClassName());
                continue;
            }
            if (referencedModels.contains(model.getClassName())) {
                filtered.addModel(model);
            }
        }

        logger.info("权限过滤完成: {} -> {} 个Controller, {} -> {} 个Model",
                apiInfo.getControllers().size(), filtered.getControllers().size(),
                apiInfo.getModels().size(), filtered.getModels().size());

        return filtered;
    }

    public OpenAPI filterOpenAPI(OpenAPI openAPI) {
        if (isDeveloper()) {
            logger.debug("开发者角色，跳过权限过滤");
            return openAPI;
        }

        logger.info("应用权限过滤到OpenAPI文档，角色: {}", allowedRoles);

        OpenAPI filtered = new OpenAPI();
        filtered.setInfo(openAPI.getInfo());
        filtered.setServers(openAPI.getServers());

        Paths filteredPaths = new Paths();
        Set<String> referencedSchemas = new HashSet<>();

        if (openAPI.getPaths() != null) {
            for (Map.Entry<String, PathItem> entry : openAPI.getPaths().entrySet()) {
                String path = entry.getKey();
                PathItem pathItem = entry.getValue();

                if (isSensitivePath(path)) {
                    logger.debug("隐藏敏感路径: {}", path);
                    continue;
                }

                PathItem filteredPathItem = filterPathItem(path, pathItem, referencedSchemas);
                if (hasAnyOperation(filteredPathItem)) {
                    filteredPaths.put(path, filteredPathItem);
                }
            }
        }
        filtered.setPaths(filteredPaths);

        if (openAPI.getTags() != null) {
            List<Tag> filteredTags = openAPI.getTags().stream()
                    .filter(tag -> !isSensitiveTag(tag.getName()))
                    .collect(Collectors.toList());
            filtered.setTags(filteredTags);
        }

        if (openAPI.getComponents() != null && openAPI.getComponents().getSchemas() != null) {
            Map<String, io.swagger.v3.oas.models.media.Schema> filteredSchemas = new HashMap<>();
            for (Map.Entry<String, io.swagger.v3.oas.models.media.Schema> entry :
                    openAPI.getComponents().getSchemas().entrySet()) {
                String schemaName = entry.getKey();
                if (hideInternalModels && isInternalModel(schemaName)) {
                    logger.debug("隐藏内部Schema: {}", schemaName);
                    continue;
                }
                if (referencedSchemas.contains(schemaName)) {
                    filteredSchemas.put(schemaName, entry.getValue());
                }
            }
            if (!filteredSchemas.isEmpty()) {
                filtered.components(new io.swagger.v3.oas.models.Components());
                filtered.getComponents().setSchemas(filteredSchemas);
            }
        }

        int originalPathCount = openAPI.getPaths() != null ? openAPI.getPaths().size() : 0;
        int originalSchemaCount = openAPI.getComponents() != null && openAPI.getComponents().getSchemas() != null
                ? openAPI.getComponents().getSchemas().size() : 0;
        int filteredPathCount = filtered.getPaths() != null ? filtered.getPaths().size() : 0;
        int filteredSchemaCount = filtered.getComponents() != null && filtered.getComponents().getSchemas() != null
                ? filtered.getComponents().getSchemas().size() : 0;

        logger.info("OpenAPI权限过滤完成: {} -> {} 个路径, {} -> {} 个Schema",
                originalPathCount, filteredPathCount, originalSchemaCount, filteredSchemaCount);

        return filtered;
    }

    private PathItem filterPathItem(String path, PathItem pathItem, Set<String> referencedSchemas) {
        PathItem filtered = new PathItem();
        filtered.set$ref(pathItem.get$ref());
        filtered.setSummary(pathItem.getSummary());
        filtered.setDescription(pathItem.getDescription());
        filtered.setServers(pathItem.getServers());
        filtered.setParameters(pathItem.getParameters());

        if (pathItem.getGet() != null && !isSensitiveOperation("GET", path, pathItem.getGet())) {
            filtered.setGet(pathItem.getGet());
            collectSchemasFromOperation(pathItem.getGet(), referencedSchemas);
        }
        if (pathItem.getPost() != null && !isSensitiveOperation("POST", path, pathItem.getPost())) {
            filtered.setPost(pathItem.getPost());
            collectSchemasFromOperation(pathItem.getPost(), referencedSchemas);
        }
        if (pathItem.getPut() != null && !isSensitiveOperation("PUT", path, pathItem.getPut())) {
            filtered.setPut(pathItem.getPut());
            collectSchemasFromOperation(pathItem.getPut(), referencedSchemas);
        }
        if (pathItem.getDelete() != null && !isSensitiveOperation("DELETE", path, pathItem.getDelete())) {
            filtered.setDelete(pathItem.getDelete());
            collectSchemasFromOperation(pathItem.getDelete(), referencedSchemas);
        }
        if (pathItem.getPatch() != null && !isSensitiveOperation("PATCH", path, pathItem.getPatch())) {
            filtered.setPatch(pathItem.getPatch());
            collectSchemasFromOperation(pathItem.getPatch(), referencedSchemas);
        }

        return filtered;
    }

    private boolean hasAnyOperation(PathItem pathItem) {
        return pathItem.getGet() != null || pathItem.getPost() != null ||
                pathItem.getPut() != null || pathItem.getDelete() != null ||
                pathItem.getPatch() != null;
    }

    private void collectSchemasFromOperation(Operation operation, Set<String> schemas) {
        if (operation.getRequestBody() != null && operation.getRequestBody().getContent() != null) {
            operation.getRequestBody().getContent().values().forEach(mediaType -> {
                if (mediaType.getSchema() != null) {
                    collectSchemaRefs(mediaType.getSchema(), schemas);
                }
            });
        }
        if (operation.getResponses() != null) {
            operation.getResponses().values().forEach(response -> {
                if (response.getContent() != null) {
                    response.getContent().values().forEach(mediaType -> {
                        if (mediaType.getSchema() != null) {
                            collectSchemaRefs(mediaType.getSchema(), schemas);
                        }
                    });
                }
            });
        }
    }

    private void collectSchemaRefs(io.swagger.v3.oas.models.media.Schema schema, Set<String> schemas) {
        if (schema == null) return;
        if (schema.get$ref() != null) {
            String refName = schema.get$ref().replace("#/components/schemas/", "");
            schemas.add(refName);
        }
        if (schema.getItems() != null) {
            collectSchemaRefs(schema.getItems(), schemas);
        }
        if (schema.getAdditionalProperties() != null &&
                schema.getAdditionalProperties() instanceof io.swagger.v3.oas.models.media.Schema) {
            collectSchemaRefs((io.swagger.v3.oas.models.media.Schema) schema.getAdditionalProperties(), schemas);
        }
    }

    private boolean isSensitiveController(ControllerInfo controller) {
        return isSensitiveTag(controller.getClassName()) || isSensitivePath(controller.getBasePath());
    }

    private boolean isSensitiveMethod(MethodInfo method, String basePath) {
        String fullPath = basePath + method.getPath();
        return isSensitivePath(fullPath) ||
                (method.getTags() != null && method.getTags().stream().anyMatch(this::isSensitiveTag));
    }

    private boolean isSensitiveOperation(String httpMethod, String path, Operation operation) {
        if (sensitiveMethods.contains(httpMethod + " " + path)) {
            return true;
        }
        if (operation.getTags() != null && operation.getTags().stream().anyMatch(this::isSensitiveTag)) {
            return true;
        }
        return false;
    }

    private boolean isSensitiveTag(String tag) {
        return sensitiveTags.stream().anyMatch(tag::contains);
    }

    private boolean isSensitivePath(String path) {
        if (path == null) return false;
        return sensitivePaths.stream().anyMatch(path::startsWith);
    }

    private boolean isInternalModel(String className) {
        return INTERNAL_MODEL_SUFFIXES.stream().anyMatch(className::endsWith);
    }

    private void collectReferencedModels(MethodInfo method, Set<String> models) {
        if (method.getRequestBodyType() != null) {
            extractModelNames(method.getRequestBodyType(), models);
        }
        if (method.getResponseType() != null) {
            extractModelNames(method.getResponseType(), models);
        }
    }

    private void extractModelNames(String typeName, Set<String> models) {
        if (typeName == null || typeName.isEmpty()) return;

        int genericStart = typeName.indexOf('<');
        int genericEnd = typeName.lastIndexOf('>');

        if (genericStart > 0 && genericEnd > genericStart) {
            String outerType = typeName.substring(0, genericStart).trim();
            if (!isPrimitiveType(outerType)) {
                models.add(outerType);
            }

            String genericContent = typeName.substring(genericStart + 1, genericEnd);
            for (String param : splitGenericParams(genericContent)) {
                extractModelNames(param, models);
            }
        } else {
            String cleanType = typeName.replace("[]", "").trim();
            if (!isPrimitiveType(cleanType) && !cleanType.startsWith("java.")) {
                models.add(cleanType);
            }
        }
    }

    private List<String> splitGenericParams(String content) {
        List<String> params = new ArrayList<>();
        int depth = 0;
        StringBuilder current = new StringBuilder();

        for (char c : content.toCharArray()) {
            if (c == '<') depth++;
            else if (c == '>') depth--;
            else if (c == ',' && depth == 0) {
                params.add(current.toString().trim());
                current = new StringBuilder();
                continue;
            }
            current.append(c);
        }

        if (current.length() > 0) {
            params.add(current.toString().trim());
        }

        return params;
    }

    private boolean isPrimitiveType(String type) {
        return type.equals("String") || type.equals("Integer") || type.equals("int")
                || type.equals("Long") || type.equals("long") || type.equals("Boolean")
                || type.equals("boolean") || type.equals("Double") || type.equals("double")
                || type.equals("Float") || type.equals("float") || type.equals("Short")
                || type.equals("short") || type.equals("Byte") || type.equals("byte")
                || type.equals("Character") || type.equals("char") || type.equals("void")
                || type.equals("Void") || type.equals("Date") || type.equals("LocalDate")
                || type.equals("LocalDateTime") || type.equals("BigDecimal") || type.equals("Object")
                || type.equals("List") || type.equals("Set") || type.equals("Map")
                || type.equals("Collection") || type.equals("Page");
    }
}