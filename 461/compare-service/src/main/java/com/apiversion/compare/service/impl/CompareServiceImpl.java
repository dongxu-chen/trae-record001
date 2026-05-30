package com.apiversion.compare.service.impl;

import cn.hutool.core.util.StrUtil;
import cn.hutool.json.JSONObject;
import cn.hutool.json.JSONUtil;
import com.apiversion.compare.dto.DiffItem;
import com.apiversion.compare.dto.DiffRequest;
import com.apiversion.compare.dto.DiffResponse;
import com.apiversion.compare.entity.ApiEndpoint;
import com.apiversion.compare.entity.ApiVersion;
import com.apiversion.compare.entity.DiffResult;
import com.apiversion.compare.mapper.ApiEndpointMapper;
import com.apiversion.compare.mapper.ApiVersionMapper;
import com.apiversion.compare.mapper.DiffResultMapper;
import com.apiversion.compare.service.CompareService;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;

@Slf4j
@Service
@RequiredArgsConstructor
public class CompareServiceImpl implements CompareService {

    private final ApiVersionMapper apiVersionMapper;
    private final ApiEndpointMapper apiEndpointMapper;
    private final DiffResultMapper diffResultMapper;

    private static final List<String> BREAKING_PARAM_CHANGES = Arrays.asList(
            "REQUIRED_ADDED", "TYPE_CHANGED", "FORMAT_CHANGED",
            "ENUM_REDUCED", "MAXIMUM_DECREASED", "MINIMUM_INCREASED",
            "MAX_LENGTH_DECREASED", "MIN_LENGTH_INCREASED"
    );

    private static final List<String> BREAKING_RESPONSE_CHANGES = Arrays.asList(
            "PROPERTY_REMOVED", "TYPE_CHANGED", "ENUM_REDUCED",
            "REQUIRED_ADDED", "FORMAT_CHANGED"
    );

    @Override
    public DiffResponse compareOpenApi(DiffRequest request) {
        DiffResponse response = compareOpenApiJson(request.getSourceOpenApi(), request.getTargetOpenApi());
        response.setSourceVersionId(request.getSourceVersionId());
        response.setTargetVersionId(request.getTargetVersionId());

        if (request.getSourceVersionId() != null && request.getTargetVersionId() != null) {
            saveDiffResults(response);
        }

        return response;
    }

    @Override
    public DiffResponse compareVersions(Long sourceVersionId, Long targetVersionId) {
        ApiVersion sourceVersion = apiVersionMapper.selectById(sourceVersionId);
        ApiVersion targetVersion = apiVersionMapper.selectById(targetVersionId);

        if (sourceVersion == null || targetVersion == null) {
            throw new IllegalArgumentException("版本不存在");
        }

        List<ApiEndpoint> sourceEndpoints = apiEndpointMapper.selectList(
                new QueryWrapper<ApiEndpoint>().eq("version_id", sourceVersionId));
        List<ApiEndpoint> targetEndpoints = apiEndpointMapper.selectList(
                new QueryWrapper<ApiEndpoint>().eq("version_id", targetVersionId));

        String sourceOpenApi = buildOpenApiFromEndpoints(sourceVersion, sourceEndpoints);
        String targetOpenApi = buildOpenApiFromEndpoints(targetVersion, targetEndpoints);

        DiffResponse response = compareOpenApiJson(sourceOpenApi, targetOpenApi);
        response.setSourceVersionId(sourceVersionId);
        response.setTargetVersionId(targetVersionId);
        response.setSourceVersion(sourceVersion.getVersion());
        response.setTargetVersion(targetVersion.getVersion());

        saveDiffResults(response);

        return response;
    }

    @Override
    public DiffResponse compareOpenApiJson(String sourceOpenApi, String targetOpenApi) {
        if (StrUtil.isBlank(sourceOpenApi) || StrUtil.isBlank(targetOpenApi)) {
            throw new IllegalArgumentException("OpenAPI文档不能为空");
        }

        JSONObject sourceDoc = JSONUtil.parseObj(sourceOpenApi);
        JSONObject targetDoc = JSONUtil.parseObj(targetOpenApi);

        List<DiffItem> differences = new ArrayList<>();

        comparePaths(sourceDoc, targetDoc, differences);
        compareSchemas(sourceDoc, targetDoc, differences);

        int addedCount = (int) differences.stream().filter(d -> "ADD".equals(d.getChangeType())).count();
        int deletedCount = (int) differences.stream().filter(d -> "DELETE".equals(d.getChangeType())).count();
        int modifiedCount = (int) differences.stream().filter(d -> "MODIFY".equals(d.getChangeType())).count();
        int breakingCount = (int) differences.stream().filter(DiffItem::getBreakingChange).count();
        boolean compatible = breakingCount == 0;

        DiffResponse response = new DiffResponse();
        response.setTotalChanges(differences.size());
        response.setAddedCount(addedCount);
        response.setDeletedCount(deletedCount);
        response.setModifiedCount(modifiedCount);
        response.setBreakingChangesCount(breakingCount);
        response.setCompatible(compatible);
        response.setDifferences(differences);
        response.setCompareTime(LocalDateTime.now());

        return response;
    }

    private void comparePaths(JSONObject sourceDoc, JSONObject targetDoc, List<DiffItem> differences) {
        JSONObject sourcePaths = sourceDoc.getJSONObject("paths");
        JSONObject targetPaths = targetDoc.getJSONObject("paths");

        if (sourcePaths == null) sourcePaths = new JSONObject();
        if (targetPaths == null) targetPaths = new JSONObject();

        Set<String> sourcePathKeys = sourcePaths.keySet();
        Set<String> targetPathKeys = targetPaths.keySet();

        for (String path : targetPathKeys) {
            if (!sourcePathKeys.contains(path)) {
                JSONObject targetPath = targetPaths.getJSONObject(path);
                for (String method : targetPath.keySet()) {
                    DiffItem item = createDiffItem("ENDPOINT", "ADD",
                            method.toUpperCase() + " " + path,
                            null, targetPath.getJSONObject(method).toString(),
                            false, "新增接口: " + method.toUpperCase() + " " + path);
                    differences.add(item);
                }
            } else {
                comparePathOperations(path, sourcePaths.getJSONObject(path),
                        targetPaths.getJSONObject(path), differences);
            }
        }

        for (String path : sourcePathKeys) {
            if (!targetPathKeys.contains(path)) {
                JSONObject sourcePath = sourcePaths.getJSONObject(path);
                for (String method : sourcePath.keySet()) {
                    DiffItem item = createDiffItem("ENDPOINT", "DELETE",
                            method.toUpperCase() + " " + path,
                            sourcePath.getJSONObject(method).toString(), null,
                            true, "删除接口: " + method.toUpperCase() + " " + path);
                    differences.add(item);
                }
            }
        }
    }

    private void comparePathOperations(String path, JSONObject sourcePath, JSONObject targetPath, List<DiffItem> differences) {
        Set<String> httpMethods = new HashSet<>();
        httpMethods.addAll(sourcePath.keySet());
        httpMethods.addAll(targetPath.keySet());

        for (String method : httpMethods) {
            String fullPath = method.toUpperCase() + " " + path;
            boolean sourceHas = sourcePath.containsKey(method);
            boolean targetHas = targetPath.containsKey(method);

            if (sourceHas && !targetHas) {
                DiffItem item = createDiffItem("ENDPOINT", "DELETE", fullPath,
                        sourcePath.getJSONObject(method).toString(), null,
                        true, "删除接口方法: " + fullPath);
                differences.add(item);
            } else if (!sourceHas && targetHas) {
                DiffItem item = createDiffItem("ENDPOINT", "ADD", fullPath,
                        null, targetPath.getJSONObject(method).toString(),
                        false, "新增接口方法: " + fullPath);
                differences.add(item);
            } else {
                JSONObject sourceOp = sourcePath.getJSONObject(method);
                JSONObject targetOp = targetPath.getJSONObject(method);
                compareOperation(fullPath, sourceOp, targetOp, differences);
            }
        }
    }

    private void compareOperation(String fullPath, JSONObject sourceOp, JSONObject targetOp, List<DiffItem> differences) {
        compareParameters(fullPath, sourceOp, targetOp, differences);
        compareRequestBody(fullPath, sourceOp, targetOp, differences);
        compareResponses(fullPath, sourceOp, targetOp, differences);
    }

    private void compareParameters(String fullPath, JSONObject sourceOp, JSONObject targetOp, List<DiffItem> differences) {
        List<JSONObject> sourceParams = getParameters(sourceOp);
        List<JSONObject> targetParams = getParameters(targetOp);

        Map<String, JSONObject> sourceParamMap = new HashMap<>();
        Map<String, JSONObject> targetParamMap = new HashMap<>();

        for (JSONObject param : sourceParams) {
            String key = param.getStr("in") + ":" + param.getStr("name");
            sourceParamMap.put(key, param);
        }
        for (JSONObject param : targetParams) {
            String key = param.getStr("in") + ":" + param.getStr("name");
            targetParamMap.put(key, param);
        }

        for (Map.Entry<String, JSONObject> entry : targetParamMap.entrySet()) {
            String key = entry.getKey();
            JSONObject targetParam = entry.getValue();
            String paramName = targetParam.getStr("name");

            if (!sourceParamMap.containsKey(key)) {
                boolean required = targetParam.getBool("required", false);
                DiffItem item = createDiffItem("PARAM", "ADD",
                        fullPath + " -> 参数[" + paramName + "]",
                        null, targetParam.toString(),
                        required, "新增参数" + (required ? "(必填)" : "(可选)") + ": " + paramName);
                differences.add(item);
            } else {
                JSONObject sourceParam = sourceParamMap.get(key);
                compareParameter(fullPath, paramName, sourceParam, targetParam, differences);
            }
        }

        for (Map.Entry<String, JSONObject> entry : sourceParamMap.entrySet()) {
            String key = entry.getKey();
            if (!targetParamMap.containsKey(key)) {
                JSONObject sourceParam = entry.getValue();
                String paramName = sourceParam.getStr("name");
                DiffItem item = createDiffItem("PARAM", "DELETE",
                        fullPath + " -> 参数[" + paramName + "]",
                        sourceParam.toString(), null,
                        true, "删除参数: " + paramName);
                differences.add(item);
            }
        }
    }

    private List<JSONObject> getParameters(JSONObject op) {
        List<JSONObject> params = new ArrayList<>();
        if (op.containsKey("parameters")) {
            params.addAll(op.getJSONArray("parameters").toList(JSONObject.class));
        }
        return params;
    }

    private void compareParameter(String fullPath, String paramName, JSONObject sourceParam, JSONObject targetParam, List<DiffItem> differences) {
        String paramPath = fullPath + " -> 参数[" + paramName + "]";

        boolean sourceRequired = sourceParam.getBool("required", false);
        boolean targetRequired = targetParam.getBool("required", false);
        if (!sourceRequired && targetRequired) {
            DiffItem item = createDiffItem("PARAM", "MODIFY",
                    paramPath + ".required",
                    String.valueOf(sourceRequired), String.valueOf(targetRequired),
                    true, "参数由可选改为必填: " + paramName);
            differences.add(item);
        }

        String sourceType = getParamType(sourceParam);
        String targetType = getParamType(targetParam);
        if (!Objects.equals(sourceType, targetType)) {
            DiffItem item = createDiffItem("PARAM", "MODIFY",
                    paramPath + ".type",
                    sourceType, targetType,
                    isBreakingTypeChange(sourceType, targetType),
                    "参数类型变更: " + paramName + " " + sourceType + " -> " + targetType);
            differences.add(item);
        }

        String sourceFormat = sourceParam.getStr("format");
        String targetFormat = targetParam.getStr("format");
        if (!Objects.equals(sourceFormat, targetFormat)) {
            DiffItem item = createDiffItem("PARAM", "MODIFY",
                    paramPath + ".format",
                    sourceFormat, targetFormat,
                    true, "参数格式变更: " + paramName);
            differences.add(item);
        }

        JSONObject sourceSchema = sourceParam.getJSONObject("schema");
        JSONObject targetSchema = targetParam.getJSONObject("schema");
        if (sourceSchema != null && targetSchema != null) {
            compareSchemaConstraints(paramPath, sourceSchema, targetSchema, differences, "PARAM");
        }
    }

    private String getParamType(JSONObject param) {
        JSONObject schema = param.getJSONObject("schema");
        if (schema != null && schema.containsKey("type")) {
            return schema.getStr("type");
        }
        return param.getStr("type");
    }

    private boolean isBreakingTypeChange(String sourceType, String targetType) {
        if (sourceType == null || targetType == null) return true;
        if (sourceType.equals(targetType)) return false;

        Map<String, List<String>> compatibleTypes = new HashMap<>();
        compatibleTypes.put("integer", Arrays.asList("number", "string"));
        compatibleTypes.put("number", Arrays.asList("string"));
        compatibleTypes.put("boolean", Arrays.asList("string"));

        List<String> compatible = compatibleTypes.get(sourceType);
        return compatible == null || !compatible.contains(targetType);
    }

    private void compareRequestBody(String fullPath, JSONObject sourceOp, JSONObject targetOp, List<DiffItem> differences) {
        JSONObject sourceBody = sourceOp.getJSONObject("requestBody");
        JSONObject targetBody = targetOp.getJSONObject("requestBody");

        String bodyPath = fullPath + " -> 请求体";

        if (sourceBody == null && targetBody != null) {
            boolean required = targetBody.getBool("required", false);
            DiffItem item = createDiffItem("PARAM", "ADD", bodyPath,
                    null, targetBody.toString(),
                    required, "新增请求体" + (required ? "(必填)" : "(可选)"));
            differences.add(item);
        } else if (sourceBody != null && targetBody == null) {
            DiffItem item = createDiffItem("PARAM", "DELETE", bodyPath,
                    sourceBody.toString(), null,
                    true, "删除请求体");
            differences.add(item);
        } else if (sourceBody != null && targetBody != null) {
            boolean sourceRequired = sourceBody.getBool("required", false);
            boolean targetRequired = targetBody.getBool("required", false);
            if (!sourceRequired && targetRequired) {
                DiffItem item = createDiffItem("PARAM", "MODIFY",
                        bodyPath + ".required",
                        String.valueOf(sourceRequired), String.valueOf(targetRequired),
                        true, "请求体由可选改为必填");
                differences.add(item);
            }

            JSONObject sourceContent = sourceBody.getJSONObject("content");
            JSONObject targetContent = targetBody.getJSONObject("content");
            if (sourceContent != null && targetContent != null) {
                compareMediaType(bodyPath, sourceContent, targetContent, differences, "PARAM");
            }
        }
    }

    private void compareResponses(String fullPath, JSONObject sourceOp, JSONObject targetOp, List<DiffItem> differences) {
        JSONObject sourceResponses = sourceOp.getJSONObject("responses");
        JSONObject targetResponses = targetOp.getJSONObject("responses");

        if (sourceResponses == null) sourceResponses = new JSONObject();
        if (targetResponses == null) targetResponses = new JSONObject();

        Set<String> sourceCodes = sourceResponses.keySet();
        Set<String> targetCodes = targetResponses.keySet();

        for (String code : targetCodes) {
            if (!sourceCodes.contains(code)) {
                if (!"200".equals(code) && !"201".equals(code) && !code.startsWith("2")) {
                    continue;
                }
                DiffItem item = createDiffItem("RESPONSE", "ADD",
                        fullPath + " -> 响应[" + code + "]",
                        null, targetResponses.getJSONObject(code).toString(),
                        false, "新增响应码: " + code);
                differences.add(item);
            } else {
                compareResponse(fullPath, code, sourceResponses.getJSONObject(code),
                        targetResponses.getJSONObject(code), differences);
            }
        }

        for (String code : sourceCodes) {
            if (!targetCodes.contains(code) && code.startsWith("2")) {
                DiffItem item = createDiffItem("RESPONSE", "DELETE",
                        fullPath + " -> 响应[" + code + "]",
                        sourceResponses.getJSONObject(code).toString(), null,
                        true, "删除成功响应码: " + code);
                differences.add(item);
            }
        }
    }

    private void compareResponse(String fullPath, String code, JSONObject sourceResp, JSONObject targetResp, List<DiffItem> differences) {
        String respPath = fullPath + " -> 响应[" + code + "]";

        JSONObject sourceContent = sourceResp.getJSONObject("content");
        JSONObject targetContent = targetResp.getJSONObject("content");

        if (sourceContent != null && targetContent != null) {
            compareMediaType(respPath, sourceContent, targetContent, differences, "RESPONSE");
        }

        compareResponseHeaders(respPath, sourceResp, targetResp, differences);
        compareResponseDescription(respPath, sourceResp, targetResp, differences);
    }

    private void compareResponseHeaders(String respPath, JSONObject sourceResp, JSONObject targetResp, List<DiffItem> differences) {
        JSONObject sourceHeaders = sourceResp.getJSONObject("headers");
        JSONObject targetHeaders = targetResp.getJSONObject("headers");

        if (sourceHeaders == null) sourceHeaders = new JSONObject();
        if (targetHeaders == null) targetHeaders = new JSONObject();

        Set<String> sourceHeaderNames = sourceHeaders.keySet();
        Set<String> targetHeaderNames = targetHeaders.keySet();

        for (String headerName : targetHeaderNames) {
            if (!sourceHeaderNames.contains(headerName)) {
                DiffItem item = createDiffItem("RESPONSE", "ADD",
                        respPath + ".headers[" + headerName + "]",
                        null, targetHeaders.getJSONObject(headerName).toString(),
                        false, "新增响应头: " + headerName);
                differences.add(item);
            } else {
                JSONObject sourceHeader = sourceHeaders.getJSONObject(headerName);
                JSONObject targetHeader = targetHeaders.getJSONObject(headerName);
                compareHeaderSchema(respPath + ".headers[" + headerName + "]", sourceHeader, targetHeader, differences);
            }
        }

        for (String headerName : sourceHeaderNames) {
            if (!targetHeaderNames.contains(headerName)) {
                DiffItem item = createDiffItem("RESPONSE", "DELETE",
                        respPath + ".headers[" + headerName + "]",
                        sourceHeaders.getJSONObject(headerName).toString(), null,
                        false, "删除响应头: " + headerName);
                differences.add(item);
            }
        }
    }

    private void compareHeaderSchema(String path, JSONObject sourceHeader, JSONObject targetHeader, List<DiffItem> differences) {
        boolean sourceRequired = sourceHeader.getBool("required", false);
        boolean targetRequired = targetHeader.getBool("required", false);
        if (!sourceRequired && targetRequired) {
            DiffItem item = createDiffItem("RESPONSE", "MODIFY",
                    path + ".required",
                    String.valueOf(sourceRequired), String.valueOf(targetRequired),
                    false, "响应头由可选改为必填");
            differences.add(item);
        }

        JSONObject sourceSchema = sourceHeader.getJSONObject("schema");
        JSONObject targetSchema = targetHeader.getJSONObject("schema");
        if (sourceSchema != null && targetSchema != null) {
            compareSchemaProperties(path + ".schema", sourceSchema, targetSchema, differences, "RESPONSE");
        }
    }

    private void compareResponseDescription(String respPath, JSONObject sourceResp, JSONObject targetResp, List<DiffItem> differences) {
        String sourceDesc = sourceResp.getStr("description");
        String targetDesc = targetResp.getStr("description");
        if (sourceDesc != null && targetDesc != null && !sourceDesc.equals(targetDesc)) {
            DiffItem item = createDiffItem("RESPONSE", "MODIFY",
                    respPath + ".description",
                    sourceDesc, targetDesc,
                    false, "响应描述变更");
            differences.add(item);
        }
    }

    private void compareSchemaProperties(String basePath, JSONObject sourceSchema, JSONObject targetSchema, List<DiffItem> differences, String diffType) {
        String sourceType = sourceSchema.getStr("type");
        String targetType = targetSchema.getStr("type");

        if (!Objects.equals(sourceType, targetType)) {
            boolean backwardCompatible = isTypeBackwardCompatible(sourceType, targetType);
            DiffItem item = createDiffItem(diffType, "MODIFY",
                    basePath + ".type", sourceType, targetType,
                    !backwardCompatible,
                    "类型变更: " + sourceType + " -> " + targetType +
                            (backwardCompatible ? " (向后兼容)" : " (不兼容)"));
            differences.add(item);
        }

        compareNumericConstraintForBackward(basePath, sourceSchema, targetSchema, differences, diffType, "minimum");
        compareNumericConstraintForBackward(basePath, sourceSchema, targetSchema, differences, diffType, "maximum");
        compareNumericConstraintForBackward(basePath, sourceSchema, targetSchema, differences, diffType, "minLength");
        compareNumericConstraintForBackward(basePath, sourceSchema, targetSchema, differences, diffType, "maxLength");
        compareStringPattern(basePath, sourceSchema, targetSchema, differences, diffType);
        compareEnumValuesForBackward(basePath, sourceSchema, targetSchema, differences, diffType);
    }

    private boolean isTypeBackwardCompatible(String sourceType, String targetType) {
        if (sourceType == null || targetType == null) {
            return false;
        }
        if (sourceType.equals(targetType)) {
            return true;
        }

        Map<String, List<String>> compatibleTypes = new HashMap<>();
        compatibleTypes.put("integer", Arrays.asList("number", "string"));
        compatibleTypes.put("number", Arrays.asList("string"));
        compatibleTypes.put("boolean", Arrays.asList("string"));
        compatibleTypes.put("array", Arrays.asList("object"));

        List<String> compatible = compatibleTypes.get(sourceType);
        return compatible != null && compatible.contains(targetType);
    }

    private void compareNumericConstraintForBackward(String basePath, JSONObject sourceSchema, JSONObject targetSchema,
                                                     List<DiffItem> differences, String diffType, String constraint) {
        if (sourceSchema.containsKey(constraint) && targetSchema.containsKey(constraint)) {
            Number sourceVal = sourceSchema.getNumber(constraint);
            Number targetVal = targetSchema.getNumber(constraint);
            int cmp = compareNumbers(sourceVal, targetVal);
            if (cmp != 0) {
                boolean backwardCompatible = isNumericConstraintBackwardCompatible(constraint, cmp);
                DiffItem item = createDiffItem(diffType, "MODIFY",
                        basePath + "." + constraint,
                        sourceVal.toString(), targetVal.toString(),
                        !backwardCompatible,
                        constraint + "变更: " + sourceVal + " -> " + targetVal +
                                (backwardCompatible ? " (向后兼容)" : " (不兼容)"));
                differences.add(item);
            }
        } else if (!sourceSchema.containsKey(constraint) && targetSchema.containsKey(constraint)) {
            Number targetVal = targetSchema.getNumber(constraint);
            DiffItem item = createDiffItem(diffType, "ADD",
                    basePath + "." + constraint,
                    null, targetVal.toString(),
                    "RESPONSE".equals(diffType) && !isAddingConstraintBackwardCompatible(constraint),
                    "新增约束" + constraint + ": " + targetVal);
            differences.add(item);
        }
    }

    private boolean isNumericConstraintBackwardCompatible(String constraint, int comparison) {
        switch (constraint) {
            case "minimum":
            case "minLength":
                return comparison <= 0;
            case "maximum":
            case "maxLength":
                return comparison >= 0;
            default:
                return false;
        }
    }

    private boolean isAddingConstraintBackwardCompatible(String constraint) {
        return "maximum".equals(constraint) || "maxLength".equals(constraint);
    }

    private void compareStringPattern(String basePath, JSONObject sourceSchema, JSONObject targetSchema,
                                       List<DiffItem> differences, String diffType) {
        String sourcePattern = sourceSchema.getStr("pattern");
        String targetPattern = targetSchema.getStr("pattern");

        if (sourcePattern != null && targetPattern != null && !sourcePattern.equals(targetPattern)) {
            DiffItem item = createDiffItem(diffType, "MODIFY",
                    basePath + ".pattern",
                    sourcePattern, targetPattern,
                    true, "正则表达式模式变更");
            differences.add(item);
        }
    }

    private void compareEnumValuesForBackward(String basePath, JSONObject sourceSchema, JSONObject targetSchema,
                                               List<DiffItem> differences, String diffType) {
        List<String> sourceEnum = getEnumValues(sourceSchema);
        List<String> targetEnum = getEnumValues(targetSchema);

        if (sourceEnum != null && targetEnum != null) {
            List<String> removed = new ArrayList<>(sourceEnum);
            removed.removeAll(targetEnum);
            if (!removed.isEmpty()) {
                DiffItem item = createDiffItem(diffType, "MODIFY",
                        basePath + ".enum",
                        sourceEnum.toString(), targetEnum.toString(),
                        true, "枚举值减少: " + removed + " (不兼容)");
                differences.add(item);
            }

            List<String> added = new ArrayList<>(targetEnum);
            added.removeAll(sourceEnum);
            if (!added.isEmpty()) {
                DiffItem item = createDiffItem(diffType, "MODIFY",
                        basePath + ".enum",
                        sourceEnum.toString(), targetEnum.toString(),
                        false, "枚举值增加: " + added + " (向后兼容)");
                differences.add(item);
            }
        }
    }

    private void compareMediaType(String basePath, JSONObject sourceContent, JSONObject targetContent, List<DiffItem> differences, String diffType) {
        String jsonType = "application/json";
        JSONObject sourceJson = sourceContent.getJSONObject(jsonType);
        JSONObject targetJson = targetContent.getJSONObject(jsonType);

        if (sourceJson == null || targetJson == null) return;

        JSONObject sourceSchema = sourceJson.getJSONObject("schema");
        JSONObject targetSchema = targetJson.getJSONObject("schema");

        if (sourceSchema != null && targetSchema != null) {
            compareSchema(basePath + ".schema", sourceSchema, targetSchema, differences, diffType);
        }
    }

    private void compareSchema(String basePath, JSONObject sourceSchema, JSONObject targetSchema, List<DiffItem> differences, String diffType) {
        String sourceType = sourceSchema.getStr("type");
        String targetType = targetSchema.getStr("type");

        if ("object".equals(sourceType) && "object".equals(targetType)) {
            compareObjectSchema(basePath, sourceSchema, targetSchema, differences, diffType);
        } else if ("array".equals(sourceType) && "array".equals(targetType)) {
            JSONObject sourceItems = sourceSchema.getJSONObject("items");
            JSONObject targetItems = targetSchema.getJSONObject("items");
            if (sourceItems != null && targetItems != null) {
                compareSchema(basePath + ".items", sourceItems, targetItems, differences, diffType);
            }
        } else if (!Objects.equals(sourceType, targetType)) {
            DiffItem item = createDiffItem(diffType, "MODIFY",
                    basePath + ".type", sourceType, targetType,
                    true, "类型变更: " + sourceType + " -> " + targetType);
            differences.add(item);
        }

        compareSchemaConstraints(basePath, sourceSchema, targetSchema, differences, diffType);
    }

    private void compareObjectSchema(String basePath, JSONObject sourceSchema, JSONObject targetSchema, List<DiffItem> differences, String diffType) {
        JSONObject sourceProps = sourceSchema.getJSONObject("properties");
        JSONObject targetProps = targetSchema.getJSONObject("properties");

        if (sourceProps == null) sourceProps = new JSONObject();
        if (targetProps == null) targetProps = new JSONObject();

        Set<String> sourceKeys = sourceProps.keySet();
        Set<String> targetKeys = targetProps.keySet();

        List<String> sourceRequired = sourceSchema.containsKey("required")
                ? sourceSchema.getJSONArray("required").toList(String.class)
                : new ArrayList<>();
        List<String> targetRequired = targetSchema.containsKey("required")
                ? targetSchema.getJSONArray("required").toList(String.class)
                : new ArrayList<>();

        for (String prop : targetKeys) {
            String propPath = basePath + ".properties." + prop;
            if (!sourceKeys.contains(prop)) {
                boolean required = targetRequired.contains(prop);
                DiffItem item = createDiffItem("SCHEMA", "ADD", propPath,
                        null, targetProps.getJSONObject(prop).toString(),
                        "RESPONSE".equals(diffType) && required,
                        "新增属性" + (required ? "(必填)" : "(可选)") + ": " + prop);
                differences.add(item);
            } else {
                if (!sourceRequired.contains(prop) && targetRequired.contains(prop)) {
                    DiffItem item = createDiffItem("SCHEMA", "MODIFY",
                            propPath + ".required", "false", "true",
                            "RESPONSE".equals(diffType),
                            "属性由可选改为必填: " + prop);
                    differences.add(item);
                }
                compareSchema(propPath, sourceProps.getJSONObject(prop),
                        targetProps.getJSONObject(prop), differences, diffType);
            }
        }

        for (String prop : sourceKeys) {
            if (!targetKeys.contains(prop)) {
                String propPath = basePath + ".properties." + prop;
                DiffItem item = createDiffItem("SCHEMA", "DELETE", propPath,
                        sourceProps.getJSONObject(prop).toString(), null,
                        true, "删除属性: " + prop);
                differences.add(item);
            }
        }
    }

    private void compareSchemaConstraints(String basePath, JSONObject sourceSchema, JSONObject targetSchema, List<DiffItem> differences, String diffType) {
        compareNumericConstraint(basePath, sourceSchema, targetSchema, differences, diffType, "minimum", true);
        compareNumericConstraint(basePath, sourceSchema, targetSchema, differences, diffType, "maximum", false);
        compareNumericConstraint(basePath, sourceSchema, targetSchema, differences, diffType, "minLength", true);
        compareNumericConstraint(basePath, sourceSchema, targetSchema, differences, diffType, "maxLength", false);

        List<String> sourceEnum = getEnumValues(sourceSchema);
        List<String> targetEnum = getEnumValues(targetSchema);

        if (sourceEnum != null && targetEnum != null) {
            List<String> removed = new ArrayList<>(sourceEnum);
            removed.removeAll(targetEnum);
            if (!removed.isEmpty()) {
                DiffItem item = createDiffItem(diffType, "MODIFY",
                        basePath + ".enum",
                        sourceEnum.toString(), targetEnum.toString(),
                        true, "枚举值减少: " + removed);
                differences.add(item);
            }
        }
    }

    private void compareNumericConstraint(String basePath, JSONObject sourceSchema, JSONObject targetSchema, List<DiffItem> differences, String diffType, String constraint, boolean increaseIsBreaking) {
        if (sourceSchema.containsKey(constraint) && targetSchema.containsKey(constraint)) {
            Number sourceVal = sourceSchema.getNumber(constraint);
            Number targetVal = targetSchema.getNumber(constraint);
            int cmp = compareNumbers(sourceVal, targetVal);
            if (cmp != 0) {
                boolean breaking = increaseIsBreaking ? cmp < 0 : cmp > 0;
                DiffItem item = createDiffItem(diffType, "MODIFY",
                        basePath + "." + constraint,
                        sourceVal.toString(), targetVal.toString(),
                        breaking,
                        constraint + "变更: " + sourceVal + " -> " + targetVal);
                differences.add(item);
            }
        }
    }

    private int compareNumbers(Number n1, Number n2) {
        return Double.compare(n1.doubleValue(), n2.doubleValue());
    }

    private List<String> getEnumValues(JSONObject schema) {
        if (schema.containsKey("enum")) {
            return schema.getJSONArray("enum").toList(String.class);
        }
        return null;
    }

    private void compareSchemas(JSONObject sourceDoc, JSONObject targetDoc, List<DiffItem> differences) {
        JSONObject sourceComponents = sourceDoc.getJSONObject("components");
        JSONObject targetComponents = targetDoc.getJSONObject("components");

        if (sourceComponents == null || targetComponents == null) return;

        JSONObject sourceSchemas = sourceComponents.getJSONObject("schemas");
        JSONObject targetSchemas = targetComponents.getJSONObject("schemas");

        if (sourceSchemas == null) sourceSchemas = new JSONObject();
        if (targetSchemas == null) targetSchemas = new JSONObject();

        Set<String> sourceKeys = sourceSchemas.keySet();
        Set<String> targetKeys = targetSchemas.keySet();

        for (String schemaName : targetKeys) {
            if (!sourceKeys.contains(schemaName)) {
                DiffItem item = createDiffItem("SCHEMA", "ADD",
                        "#/components/schemas/" + schemaName,
                        null, targetSchemas.getJSONObject(schemaName).toString(),
                        false, "新增模型: " + schemaName);
                differences.add(item);
            } else {
                compareSchema("#/components/schemas/" + schemaName,
                        sourceSchemas.getJSONObject(schemaName),
                        targetSchemas.getJSONObject(schemaName),
                        differences, "SCHEMA");
            }
        }

        for (String schemaName : sourceKeys) {
            if (!targetKeys.contains(schemaName)) {
                DiffItem item = createDiffItem("SCHEMA", "DELETE",
                        "#/components/schemas/" + schemaName,
                        sourceSchemas.getJSONObject(schemaName).toString(), null,
                        true, "删除模型: " + schemaName);
                differences.add(item);
            }
        }
    }

    private DiffItem createDiffItem(String diffType, String changeType, String changePath,
                                    String oldValue, String newValue,
                                    boolean breakingChange, String description) {
        DiffItem item = new DiffItem();
        item.setDiffType(diffType);
        item.setChangeType(changeType);
        item.setChangePath(changePath);
        item.setOldValue(oldValue);
        item.setNewValue(newValue);
        item.setBreakingChange(breakingChange);
        item.setDescription(description);
        return item;
    }

    private String buildOpenApiFromEndpoints(ApiVersion version, List<ApiEndpoint> endpoints) {
        JSONObject openapi = new JSONObject();
        openapi.set("openapi", "3.0.0");

        JSONObject info = new JSONObject();
        info.set("title", version.getServiceName());
        info.set("version", version.getVersion());
        info.set("description", version.getDescription());
        openapi.set("info", info);

        JSONObject paths = new JSONObject();
        for (ApiEndpoint endpoint : endpoints) {
            String path = endpoint.getApiPath();
            String method = endpoint.getHttpMethod().toLowerCase();

            if (!paths.containsKey(path)) {
                paths.set(path, new JSONObject());
            }

            JSONObject pathObj = paths.getJSONObject(path);
            JSONObject operation = new JSONObject();
            operation.set("operationId", method + "_" + path.replaceAll("/", "_").replaceAll("[{}]", ""));

            if (StrUtil.isNotBlank(endpoint.getRequestParams())) {
                try {
                    operation.set("parameters", JSONUtil.parseArray(endpoint.getRequestParams()));
                } catch (Exception e) {
                    log.warn("解析请求参数失败: {}", endpoint.getRequestParams());
                }
            }

            if (StrUtil.isNotBlank(endpoint.getResponseParams())) {
                try {
                    JSONObject responses = new JSONObject();
                    JSONObject okResp = new JSONObject();
                    JSONObject content = new JSONObject();
                    JSONObject jsonContent = new JSONObject();
                    jsonContent.set("schema", JSONUtil.parseObj(endpoint.getResponseParams()));
                    content.set("application/json", jsonContent);
                    okResp.set("content", content);
                    responses.set("200", okResp);
                    operation.set("responses", responses);
                } catch (Exception e) {
                    log.warn("解析响应参数失败: {}", endpoint.getResponseParams());
                }
            }

            pathObj.set(method, operation);
        }
        openapi.set("paths", paths);

        return openapi.toString();
    }

    private void saveDiffResults(DiffResponse response) {
        if (response.getDifferences() == null) return;

        for (DiffItem item : response.getDifferences()) {
            DiffResult result = new DiffResult();
            result.setSourceVersionId(response.getSourceVersionId());
            result.setTargetVersionId(response.getTargetVersionId());
            result.setDiffType(item.getDiffType());
            result.setChangeType(item.getChangeType());
            result.setChangePath(item.getChangePath());
            result.setOldValue(item.getOldValue());
            result.setNewValue(item.getNewValue());
            result.setCompatible(!item.getBreakingChange());
            diffResultMapper.insert(result);
        }
    }
}
