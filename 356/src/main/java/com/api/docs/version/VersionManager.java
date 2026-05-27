package com.api.docs.version;

import com.api.docs.config.GeneratorConfig;
import io.swagger.v3.core.util.Json;
import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.Operation;
import io.swagger.v3.oas.models.PathItem;
import io.swagger.v3.oas.models.parameters.Parameter;
import io.swagger.v3.oas.models.parameters.RequestBody;
import io.swagger.v3.oas.models.responses.ApiResponse;
import io.swagger.v3.oas.models.media.Schema;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.*;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.util.*;

public class VersionManager {
    private static final Logger logger = LoggerFactory.getLogger(VersionManager.class);
    private final GeneratorConfig config;
    private final Path versionsDir;

    public VersionManager(GeneratorConfig config) throws IOException {
        this.config = config;
        this.versionsDir = Paths.get(config.getOutputPath(), "versions");
        if (!Files.exists(versionsDir)) {
            Files.createDirectories(versionsDir);
        }
    }

    public void saveVersion(OpenAPI openAPI, String version) throws IOException {
        String versionFileName = version.replace(".", "_") + ".json";
        Path versionFile = versionsDir.resolve(versionFileName);

        String content = Json.pretty().writeValueAsString(openAPI);
        Files.write(versionFile, content.getBytes(),
                StandardOpenOption.CREATE, StandardOpenOption.TRUNCATE_EXISTING);

        logger.info("版本 {} 已保存: {}", version, versionFile);
        updateVersionIndex(version);
    }

    public OpenAPI loadVersion(String version) throws IOException {
        String versionFileName = version.replace(".", "_") + ".json";
        Path versionFile = versionsDir.resolve(versionFileName);

        if (!Files.exists(versionFile)) {
            throw new FileNotFoundException("版本 " + version + " 不存在");
        }

        String content = new String(Files.readAllBytes(versionFile));
        return Json.mapper().readValue(content, OpenAPI.class);
    }

    public List<String> listVersions() throws IOException {
        List<String> versions = new ArrayList<>();
        Path indexFile = versionsDir.resolve("index.txt");

        if (Files.exists(indexFile)) {
            List<String> lines = Files.readAllLines(indexFile);
            versions.addAll(lines);
        }

        return versions;
    }

    private void updateVersionIndex(String version) throws IOException {
        Path indexFile = versionsDir.resolve("index.txt");
        List<String> versions = new ArrayList<>();

        if (Files.exists(indexFile)) {
            versions.addAll(Files.readAllLines(indexFile));
        }

        if (!versions.contains(version)) {
            versions.add(version);
            Files.write(indexFile, versions, StandardOpenOption.CREATE, StandardOpenOption.TRUNCATE_EXISTING);
        }
    }

    public VersionDiff compareVersions(String version1, String version2) throws IOException {
        OpenAPI oldApi = loadVersion(version1);
        OpenAPI newApi = loadVersion(version2);

        return compareOpenAPI(oldApi, newApi, version1, version2);
    }

    private VersionDiff compareOpenAPI(OpenAPI oldApi, OpenAPI newApi, String v1, String v2) {
        VersionDiff diff = new VersionDiff();
        diff.setOldVersion(v1);
        diff.setNewVersion(v2);

        Map<String, PathItem> oldPaths = oldApi.getPaths();
        Map<String, PathItem> newPaths = newApi.getPaths();

        Set<String> allPaths = new HashSet<>();
        if (oldPaths != null) allPaths.addAll(oldPaths.keySet());
        if (newPaths != null) allPaths.addAll(newPaths.keySet());

        for (String path : allPaths) {
            PathItem oldPathItem = oldPaths != null ? oldPaths.get(path) : null;
            PathItem newPathItem = newPaths != null ? newPaths.get(path) : null;

            if (oldPathItem == null && newPathItem != null) {
                diff.addAddedPath(path);
            } else if (oldPathItem != null && newPathItem == null) {
                diff.addRemovedPath(path);
            } else {
                comparePathOperations(path, oldPathItem, newPathItem, diff);
            }
        }

        Map<String, Schema> oldSchemas = oldApi.getComponents() != null
                ? oldApi.getComponents().getSchemas() : null;
        Map<String, Schema> newSchemas = newApi.getComponents() != null
                ? newApi.getComponents().getSchemas() : null;

        Set<String> allSchemas = new HashSet<>();
        if (oldSchemas != null) allSchemas.addAll(oldSchemas.keySet());
        if (newSchemas != null) allSchemas.addAll(newSchemas.keySet());

        for (String schemaName : allSchemas) {
            Schema oldSchema = oldSchemas != null ? oldSchemas.get(schemaName) : null;
            Schema newSchema = newSchemas != null ? newSchemas.get(schemaName) : null;

            if (oldSchema == null && newSchema != null) {
                diff.addAddedSchema(schemaName);
            } else if (oldSchema != null && newSchema == null) {
                diff.addRemovedSchema(schemaName);
            } else {
                compareSchemas(schemaName, oldSchema, newSchema, diff);
            }
        }

        return diff;
    }

    private void comparePathOperations(String path,
                                       PathItem oldItem,
                                       PathItem newItem,
                                       VersionDiff diff) {
        List<String> methods = Arrays.asList("GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS");

        for (String method : methods) {
            Operation oldOp = getOperation(oldItem, method);
            Operation newOp = getOperation(newItem, method);

            if (oldOp == null && newOp != null) {
                OperationChangeDetail change = new OperationChangeDetail();
                change.setOperationPath(path);
                change.setHttpMethod(method);
                change.setChangeType(OperationChangeDetail.ChangeType.ADDED);
                change.setNewSummary(newOp.getSummary());
                change.setNewDeprecated(newOp.getDeprecated());
                diff.addOperationChange(change);
            } else if (oldOp != null && newOp == null) {
                OperationChangeDetail change = new OperationChangeDetail();
                change.setOperationPath(path);
                change.setHttpMethod(method);
                change.setChangeType(OperationChangeDetail.ChangeType.REMOVED);
                change.setOldSummary(oldOp.getSummary());
                change.setOldDeprecated(oldOp.getDeprecated());
                diff.addOperationChange(change);
            } else if (oldOp != null && newOp != null) {
                compareOperations(path, method, oldOp, newOp, diff);
            }
        }
    }

    private Operation getOperation(PathItem item, String method) {
        if (item == null) return null;
        switch (method) {
            case "GET": return item.getGet();
            case "POST": return item.getPost();
            case "PUT": return item.getPut();
            case "DELETE": return item.getDelete();
            case "PATCH": return item.getPatch();
            case "HEAD": return item.getHead();
            case "OPTIONS": return item.getOptions();
            default: return null;
        }
    }

    private void compareOperations(String path, String method,
                                   Operation oldOp, Operation newOp,
                                   VersionDiff diff) {
        boolean hasChanges = false;
        OperationChangeDetail change = new OperationChangeDetail();
        change.setOperationPath(path);
        change.setHttpMethod(method);
        change.setChangeType(OperationChangeDetail.ChangeType.MODIFIED);

        if (!safeEquals(oldOp.getSummary(), newOp.getSummary())) {
            change.setOldSummary(oldOp.getSummary());
            change.setNewSummary(newOp.getSummary());
            hasChanges = true;
        }

        if (!safeEquals(oldOp.getDeprecated(), newOp.getDeprecated())) {
            change.setOldDeprecated(oldOp.getDeprecated());
            change.setNewDeprecated(newOp.getDeprecated());
            hasChanges = true;
        }

        List<ParameterChangeDetail> paramChanges = compareParameters(oldOp.getParameters(), newOp.getParameters());
        if (!paramChanges.isEmpty()) {
            change.setParameterChanges(paramChanges);
            hasChanges = true;
        }

        String oldRequestBodyType = getRequestBodyType(oldOp.getRequestBody());
        String newRequestBodyType = getRequestBodyType(newOp.getRequestBody());
        if (!safeEquals(oldRequestBodyType, newRequestBodyType)) {
            change.setOldRequestBodyType(oldRequestBodyType);
            change.setNewRequestBodyType(newRequestBodyType);
            hasChanges = true;
        }

        String oldResponseType = getResponseType(oldOp.getResponses());
        String newResponseType = getResponseType(newOp.getResponses());
        if (!safeEquals(oldResponseType, newResponseType)) {
            change.setOldResponseType(oldResponseType);
            change.setNewResponseType(newResponseType);
            hasChanges = true;
        }

        if (hasChanges) {
            diff.addOperationChange(change);
        }
    }

    private List<ParameterChangeDetail> compareParameters(List<Parameter> oldParams, List<Parameter> newParams) {
        List<ParameterChangeDetail> changes = new ArrayList<>();

        Map<String, Parameter> oldParamMap = new HashMap<>();
        if (oldParams != null) {
            for (Parameter p : oldParams) {
                oldParamMap.put(p.getName() + ":" + p.getIn(), p);
            }
        }

        Map<String, Parameter> newParamMap = new HashMap<>();
        if (newParams != null) {
            for (Parameter p : newParams) {
                newParamMap.put(p.getName() + ":" + p.getIn(), p);
            }
        }

        Set<String> allKeys = new HashSet<>();
        allKeys.addAll(oldParamMap.keySet());
        allKeys.addAll(newParamMap.keySet());

        for (String key : allKeys) {
            Parameter oldP = oldParamMap.get(key);
            Parameter newP = newParamMap.get(key);

            if (oldP == null && newP != null) {
                ParameterChangeDetail change = new ParameterChangeDetail();
                change.setParameterName(newP.getName());
                change.setChangeType(ParameterChangeDetail.ChangeType.ADDED);
                change.setNewIn(newP.getIn());
                change.setNewType(getSchemaType(newP.getSchema()));
                change.setNewRequired(newP.getRequired());
                changes.add(change);
            } else if (oldP != null && newP == null) {
                ParameterChangeDetail change = new ParameterChangeDetail();
                change.setParameterName(oldP.getName());
                change.setChangeType(ParameterChangeDetail.ChangeType.REMOVED);
                change.setOldIn(oldP.getIn());
                change.setOldType(getSchemaType(oldP.getSchema()));
                change.setOldRequired(oldP.getRequired());
                changes.add(change);
            } else if (oldP != null && newP != null) {
                boolean paramChanged = false;
                ParameterChangeDetail change = new ParameterChangeDetail();
                change.setParameterName(newP.getName());

                if (!safeEquals(getSchemaType(oldP.getSchema()), getSchemaType(newP.getSchema()))) {
                    change.setOldType(getSchemaType(oldP.getSchema()));
                    change.setNewType(getSchemaType(newP.getSchema()));
                    change.setChangeType(ParameterChangeDetail.ChangeType.TYPE_CHANGED);
                    paramChanged = true;
                }

                if (!safeEquals(oldP.getRequired(), newP.getRequired())) {
                    change.setOldRequired(oldP.getRequired());
                    change.setNewRequired(newP.getRequired());
                    if (change.getChangeType() == null) {
                        change.setChangeType(ParameterChangeDetail.ChangeType.REQUIRED_CHANGED);
                    }
                    paramChanged = true;
                }

                if (paramChanged) {
                    if (change.getChangeType() == null) {
                        change.setChangeType(ParameterChangeDetail.ChangeType.OTHER);
                    }
                    changes.add(change);
                }
            }
        }

        return changes;
    }

    private String getRequestBodyType(RequestBody requestBody) {
        if (requestBody == null || requestBody.getContent() == null) return null;
        var content = requestBody.getContent().get("application/json");
        if (content == null || content.getSchema() == null) return null;
        return getSchemaRef(content.getSchema());
    }

    private String getResponseType(io.swagger.v3.oas.models.responses.ApiResponses responses) {
        if (responses == null) return null;
        ApiResponse response = responses.get("200");
        if (response == null || response.getContent() == null) return null;
        var content = response.getContent().get("application/json");
        if (content == null || content.getSchema() == null) return null;
        return getSchemaRef(content.getSchema());
    }

    private String getSchemaRef(Schema schema) {
        if (schema == null) return null;
        if (schema.get$ref() != null) {
            return schema.get$ref().replace("#/components/schemas/", "");
        }
        if (schema.getType() != null) {
            return schema.getType();
        }
        return null;
    }

    private String getSchemaType(Schema schema) {
        if (schema == null) return null;
        if (schema.getType() != null) {
            return schema.getType();
        }
        if (schema.get$ref() != null) {
            return schema.get$ref().replace("#/components/schemas/", "");
        }
        return "object";
    }

    private void compareSchemas(String name,
                                Schema oldSchema,
                                Schema newSchema,
                                VersionDiff diff) {
        Map<String, Schema> oldProps = oldSchema != null ? oldSchema.getProperties() : null;
        Map<String, Schema> newProps = newSchema != null ? newSchema.getProperties() : null;

        Set<String> allProps = new HashSet<>();
        if (oldProps != null) allProps.addAll(oldProps.keySet());
        if (newProps != null) allProps.addAll(newProps.keySet());

        boolean schemaModified = false;

        for (String prop : allProps) {
            Schema oldProp = oldProps != null ? oldProps.get(prop) : null;
            Schema newProp = newProps != null ? newProps.get(prop) : null;

            String fullProp = name + "." + prop;

            if (oldProp == null && newProp != null) {
                FieldChangeDetail change = new FieldChangeDetail();
                change.setFieldName(fullProp);
                change.setChangeType(FieldChangeDetail.ChangeType.ADDED);
                change.setNewType(getSchemaType(newProp));
                change.setNewRequired(isFieldRequired(newSchema, prop));
                diff.addFieldChange(change);
                schemaModified = true;
            } else if (oldProp != null && newProp == null) {
                FieldChangeDetail change = new FieldChangeDetail();
                change.setFieldName(fullProp);
                change.setChangeType(FieldChangeDetail.ChangeType.REMOVED);
                change.setOldType(getSchemaType(oldProp));
                change.setOldRequired(isFieldRequired(oldSchema, prop));
                diff.addFieldChange(change);
                schemaModified = true;
            } else if (oldProp != null && newProp != null) {
                FieldChangeDetail change = compareField(fullProp, oldProp, newProp, oldSchema, newSchema);
                if (change != null) {
                    diff.addFieldChange(change);
                    schemaModified = true;
                }
            }
        }

        if (schemaModified) {
            diff.addModifiedSchema(name);
        }
    }

    private FieldChangeDetail compareField(String fullProp,
                                           Schema oldProp, Schema newProp,
                                           Schema oldSchema, Schema newSchema) {
        boolean changed = false;
        FieldChangeDetail change = new FieldChangeDetail();
        change.setFieldName(fullProp);

        String oldType = getSchemaType(oldProp);
        String newType = getSchemaType(newProp);
        if (!safeEquals(oldType, newType)) {
            change.setOldType(oldType);
            change.setNewType(newType);
            change.setChangeType(FieldChangeDetail.ChangeType.TYPE_CHANGED);
            changed = true;
        }

        Boolean oldRequired = isFieldRequired(oldSchema, fullProp.substring(fullProp.lastIndexOf('.') + 1));
        Boolean newRequired = isFieldRequired(newSchema, fullProp.substring(fullProp.lastIndexOf('.') + 1));
        if (!safeEquals(oldRequired, newRequired)) {
            change.setOldRequired(oldRequired);
            change.setNewRequired(newRequired);
            if (change.getChangeType() == null) {
                change.setChangeType(FieldChangeDetail.ChangeType.REQUIRED_CHANGED);
            }
            changed = true;
        }

        String oldDesc = oldProp.getDescription();
        String newDesc = newProp.getDescription();
        if (!safeEquals(oldDesc, newDesc)) {
            change.setDescription(oldDesc + " → " + newDesc);
            if (change.getChangeType() == null) {
                change.setChangeType(FieldChangeDetail.ChangeType.DESCRIPTION_CHANGED);
            }
            changed = true;
        }

        if (changed) {
            if (change.getChangeType() == null) {
                change.setChangeType(FieldChangeDetail.ChangeType.OTHER);
            }
            return change;
        }
        return null;
    }

    private Boolean isFieldRequired(Schema schema, String fieldName) {
        if (schema == null || schema.getRequired() == null) return false;
        return schema.getRequired().contains(fieldName);
    }

    private boolean safeEquals(Object a, Object b) {
        if (a == null && b == null) return true;
        if (a == null || b == null) return false;
        return a.equals(b);
    }

    public String generateDiffReport(VersionDiff diff) {
        StringBuilder sb = new StringBuilder();
        sb.append("# API 版本差异报告\n\n");
        sb.append("**旧版本**: ").append(diff.getOldVersion()).append("\n");
        sb.append("**新版本**: ").append(diff.getNewVersion()).append("\n");
        sb.append("**生成时间**: ").append(new Date()).append("\n\n");

        if (!diff.getAddedPaths().isEmpty()) {
            sb.append("## 新增路径 (").append(diff.getAddedPaths().size()).append(")\n\n");
            for (String path : diff.getAddedPaths()) {
                sb.append("- `").append(path).append("`\n");
            }
            sb.append("\n");
        }

        if (!diff.getRemovedPaths().isEmpty()) {
            sb.append("## 移除路径 (").append(diff.getRemovedPaths().size()).append(")\n\n");
            for (String path : diff.getRemovedPaths()) {
                sb.append("- `").append(path).append("`\n");
            }
            sb.append("\n");
        }

        List<OperationChangeDetail> addedOps = new ArrayList<>();
        List<OperationChangeDetail> removedOps = new ArrayList<>();
        List<OperationChangeDetail> modifiedOps = new ArrayList<>();

        for (OperationChangeDetail op : diff.getOperationChanges()) {
            if (op.getChangeType() == OperationChangeDetail.ChangeType.ADDED) {
                addedOps.add(op);
            } else if (op.getChangeType() == OperationChangeDetail.ChangeType.REMOVED) {
                removedOps.add(op);
            } else {
                modifiedOps.add(op);
            }
        }

        if (!addedOps.isEmpty()) {
            sb.append("## 新增接口 (").append(addedOps.size()).append(")\n\n");
            for (OperationChangeDetail op : addedOps) {
                sb.append("- `").append(op.getHttpMethod()).append(" ").append(op.getOperationPath()).append("`");
                if (op.getNewSummary() != null && !op.getNewSummary().isEmpty()) {
                    sb.append(" - ").append(op.getNewSummary());
                }
                sb.append("\n");
            }
            sb.append("\n");
        }

        if (!removedOps.isEmpty()) {
            sb.append("## 移除接口 (").append(removedOps.size()).append(")\n\n");
            for (OperationChangeDetail op : removedOps) {
                sb.append("- `").append(op.getHttpMethod()).append(" ").append(op.getOperationPath()).append("`");
                if (op.getOldSummary() != null && !op.getOldSummary().isEmpty()) {
                    sb.append(" - ").append(op.getOldSummary());
                }
                sb.append("\n");
            }
            sb.append("\n");
        }

        if (!modifiedOps.isEmpty()) {
            sb.append("## 修改接口 (").append(modifiedOps.size()).append(")\n\n");
            for (OperationChangeDetail op : modifiedOps) {
                sb.append("### `").append(op.getHttpMethod()).append(" ").append(op.getOperationPath()).append("`\n\n");

                if (op.getOldSummary() != null || op.getNewSummary() != null) {
                    sb.append("- **摘要变更**: `").append(safeString(op.getOldSummary()))
                      .append("` → `").append(safeString(op.getNewSummary())).append("`\n");
                }

                if (op.getOldDeprecated() != null || op.getNewDeprecated() != null) {
                    sb.append("- **废弃状态变更**: `").append(op.getOldDeprecated())
                      .append("` → `").append(op.getNewDeprecated()).append("`\n");
                }

                if (op.getOldRequestBodyType() != null || op.getNewRequestBodyType() != null) {
                    sb.append("- **请求体类型变更**: `").append(safeString(op.getOldRequestBodyType()))
                      .append("` → `").append(safeString(op.getNewRequestBodyType())).append("`\n");
                }

                if (op.getOldResponseType() != null || op.getNewResponseType() != null) {
                    sb.append("- **响应类型变更**: `").append(safeString(op.getOldResponseType()))
                      .append("` → `").append(safeString(op.getNewResponseType())).append("`\n");
                }

                if (!op.getParameterChanges().isEmpty()) {
                    sb.append("\n**参数变更**:\n\n");
                    for (ParameterChangeDetail param : op.getParameterChanges()) {
                        sb.append("  - **").append(param.getChangeType().name()).append("**: `")
                          .append(param.getParameterName()).append("`\n");
                        if (param.getChangeType() == ParameterChangeDetail.ChangeType.TYPE_CHANGED) {
                            sb.append("    - 类型: `").append(safeString(param.getOldType()))
                              .append("` → `").append(safeString(param.getNewType())).append("`\n");
                        }
                        if (param.getChangeType() == ParameterChangeDetail.ChangeType.REQUIRED_CHANGED) {
                            sb.append("    - 必填: `").append(param.getOldRequired())
                              .append("` → `").append(param.getNewRequired()).append("`\n");
                        }
                    }
                }
                sb.append("\n");
            }
        }

        if (!diff.getAddedSchemas().isEmpty()) {
            sb.append("## 新增模型 (").append(diff.getAddedSchemas().size()).append(")\n\n");
            for (String schema : diff.getAddedSchemas()) {
                sb.append("- ").append(schema).append("\n");
            }
            sb.append("\n");
        }

        if (!diff.getRemovedSchemas().isEmpty()) {
            sb.append("## 移除模型 (").append(diff.getRemovedSchemas().size()).append(")\n\n");
            for (String schema : diff.getRemovedSchemas()) {
                sb.append("- ").append(schema).append("\n");
            }
            sb.append("\n");
        }

        if (!diff.getModifiedSchemas().isEmpty()) {
            sb.append("## 修改模型 (").append(diff.getModifiedSchemas().size()).append(")\n\n");
            for (String schema : diff.getModifiedSchemas()) {
                sb.append("- ").append(schema).append("\n");
            }
            sb.append("\n");
        }

        List<FieldChangeDetail> addedFields = new ArrayList<>();
        List<FieldChangeDetail> removedFields = new ArrayList<>();
        List<FieldChangeDetail> modifiedFields = new ArrayList<>();

        for (FieldChangeDetail field : diff.getFieldChanges()) {
            if (field.getChangeType() == FieldChangeDetail.ChangeType.ADDED) {
                addedFields.add(field);
            } else if (field.getChangeType() == FieldChangeDetail.ChangeType.REMOVED) {
                removedFields.add(field);
            } else {
                modifiedFields.add(field);
            }
        }

        if (!addedFields.isEmpty()) {
            sb.append("## 新增字段 (").append(addedFields.size()).append(")\n\n");
            sb.append("| 字段 | 类型 | 必填 |\n|------|------|------|\n");
            for (FieldChangeDetail field : addedFields) {
                sb.append("| `").append(field.getFieldName()).append("` | `")
                  .append(safeString(field.getNewType())).append("` | ")
                  .append(field.getNewRequired() != null && field.getNewRequired() ? "是" : "否").append(" |\n");
            }
            sb.append("\n");
        }

        if (!removedFields.isEmpty()) {
            sb.append("## 移除字段 (").append(removedFields.size()).append(")\n\n");
            sb.append("| 字段 | 类型 | 必填 |\n|------|------|------|\n");
            for (FieldChangeDetail field : removedFields) {
                sb.append("| `").append(field.getFieldName()).append("` | `")
                  .append(safeString(field.getOldType())).append("` | ")
                  .append(field.getOldRequired() != null && field.getOldRequired() ? "是" : "否").append(" |\n");
            }
            sb.append("\n");
        }

        if (!modifiedFields.isEmpty()) {
            sb.append("## 修改字段 (").append(modifiedFields.size()).append(")\n\n");
            sb.append("| 字段 | 变更类型 | 变更详情 |\n|------|----------|----------|\n");
            for (FieldChangeDetail field : modifiedFields) {
                String detail = "";
                if (field.getChangeType() == FieldChangeDetail.ChangeType.TYPE_CHANGED) {
                    detail = "`" + safeString(field.getOldType()) + "` → `" + safeString(field.getNewType()) + "`";
                } else if (field.getChangeType() == FieldChangeDetail.ChangeType.REQUIRED_CHANGED) {
                    detail = "`" + (field.getOldRequired() != null && field.getOldRequired() ? "是" : "否") +
                             "` → `" + (field.getNewRequired() != null && field.getNewRequired() ? "是" : "否") + "`";
                } else if (field.getChangeType() == FieldChangeDetail.ChangeType.DESCRIPTION_CHANGED) {
                    detail = safeString(field.getDescription());
                }
                sb.append("| `").append(field.getFieldName()).append("` | ")
                  .append(field.getChangeType().name()).append(" | ").append(detail).append(" |\n");
            }
            sb.append("\n");
        }

        int totalChanges = diff.getOperationChanges().size() + diff.getFieldChanges().size()
                + diff.getAddedPaths().size() + diff.getRemovedPaths().size()
                + diff.getAddedSchemas().size() + diff.getRemovedSchemas().size();

        if (totalChanges == 0) {
            sb.append("## 总结\n\n");
            sb.append("两个版本完全一致，没有发现任何差异。\n");
        } else {
            sb.append("## 总结\n\n");
            sb.append("| 变更类型 | 数量 |\n|----------|------|\n");
            sb.append("| 新增接口 | ").append(addedOps.size()).append(" |\n");
            sb.append("| 移除接口 | ").append(removedOps.size()).append(" |\n");
            sb.append("| 修改接口 | ").append(modifiedOps.size()).append(" |\n");
            sb.append("| 新增字段 | ").append(addedFields.size()).append(" |\n");
            sb.append("| 移除字段 | ").append(removedFields.size()).append(" |\n");
            sb.append("| 修改字段 | ").append(modifiedFields.size()).append(" |\n");
            sb.append("| **总计** | **").append(totalChanges).append("** |\n");
        }

        return sb.toString();
    }

    private String safeString(String s) {
        return s != null ? s : "";
    }

    public void saveDiffReport(VersionDiff diff, String outputPath) throws IOException {
        Path outputDir = Paths.get(outputPath);
        if (!Files.exists(outputDir)) {
            Files.createDirectories(outputDir);
        }

        String report = generateDiffReport(diff);
        Path reportFile = outputDir.resolve("diff-report-" + diff.getOldVersion() + "-" + diff.getNewVersion() + ".md");
        Files.write(reportFile, report.getBytes());

        logger.info("差异报告已保存: {}", reportFile);
    }
}