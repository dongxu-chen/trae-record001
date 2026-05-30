package com.api.validator.controller;

import com.api.validator.model.*;
import com.api.validator.service.*;
import com.fasterxml.jackson.databind.JsonNode;
import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.media.Schema;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api")
@CrossOrigin(origins = "*")
public class ValidationController {

    @Autowired
    private OpenApiParserService openApiParserService;

    @Autowired
    private JsonSchemaValidationService jsonSchemaValidationService;

    @Autowired
    private StreamingValidationService streamingValidationService;

    @Autowired
    private ResponseComparisonService responseComparisonService;

    @Autowired
    private ReportGenerationService reportGenerationService;

    @Autowired
    private MockGenerationService mockGenerationService;

    @Autowired
    private VersionCompatibilityService versionCompatibilityService;

    @Autowired
    private FixSuggestionService fixSuggestionService;

    @PostMapping("/parse")
    public ResponseEntity<?> parseOpenApi(@RequestBody Map<String, String> request) {
        try {
            String openApiSpec = request.get("openApiSpec");
            OpenAPI openAPI = openApiParserService.parseOpenApiSpec(openApiSpec);
            
            List<Map<String, String>> endpoints = openApiParserService.extractAllEndpoints(openAPI);
            
            Map<String, Object> result = new HashMap<>();
            result.put("title", openAPI.getInfo() != null ? openAPI.getInfo().getTitle() : "Unknown");
            result.put("version", openAPI.getInfo() != null ? openAPI.getInfo().getVersion() : "Unknown");
            result.put("description", openAPI.getInfo() != null ? openAPI.getInfo().getDescription() : "");
            result.put("endpoints", endpoints);
            
            return ResponseEntity.ok(result);
        } catch (Exception e) {
            Map<String, String> error = new HashMap<>();
            error.put("error", e.getMessage());
            return ResponseEntity.badRequest().body(error);
        }
    }

    @PostMapping("/validate")
    public ResponseEntity<?> validateResponse(@RequestBody ValidationRequest request) {
        try {
            OpenAPI openAPI = openApiParserService.parseOpenApiSpec(request.getOpenApiSpec());
            Schema<?> responseSchema = openApiParserService.extractResponseSchema(
                    openAPI, request.getPath(), request.getMethod(), request.getStatusCode());
            
            JsonNode jsonSchema = openApiParserService.convertSchemaToJsonSchema(responseSchema, openAPI);
            ValidationResult result = jsonSchemaValidationService.validateWithCustomChecks(
                    request.getResponseBody(), jsonSchema);
            
            result.setPath(request.getPath());
            result.setMethod(request.getMethod());
            result.setStatusCode(request.getStatusCode());
            
            return ResponseEntity.ok(result);
        } catch (Exception e) {
            ValidationResult result = new ValidationResult();
            result.setValid(false);
            result.addError("", "校验错误: " + e.getMessage(), ValidationResult.ErrorType.SCHEMA_ERROR);
            return ResponseEntity.badRequest().body(result);
        }
    }

    @PostMapping("/schema")
    public ResponseEntity<?> getSchema(@RequestBody ValidationRequest request) {
        try {
            OpenAPI openAPI = openApiParserService.parseOpenApiSpec(request.getOpenApiSpec());
            Schema<?> responseSchema = openApiParserService.extractResponseSchema(
                    openAPI, request.getPath(), request.getMethod(), request.getStatusCode());
            
            JsonNode jsonSchema = openApiParserService.convertSchemaToJsonSchema(responseSchema, openAPI);
            
            return ResponseEntity.ok(jsonSchema);
        } catch (Exception e) {
            Map<String, String> error = new HashMap<>();
            error.put("error", e.getMessage());
            return ResponseEntity.badRequest().body(error);
        }
    }

    @PostMapping("/compare")
    public ResponseEntity<?> compareResponses(@RequestBody ComparisonRequest request) {
        try {
            ComparisonResult result = responseComparisonService.compare(
                    request.getEnv1Name(),
                    request.getEnv2Name(),
                    request.getEnv1ResponseBody(),
                    request.getEnv2ResponseBody()
            );
            
            result.setPath(request.getPath());
            result.setMethod(request.getMethod());
            
            if (request.getOpenApiSpec() != null && !request.getOpenApiSpec().isEmpty()) {
                try {
                    OpenAPI openAPI = openApiParserService.parseOpenApiSpec(request.getOpenApiSpec());
                    Schema<?> responseSchema = openApiParserService.extractResponseSchema(
                            openAPI, request.getPath(), request.getMethod(), request.getStatusCode());
                    JsonNode jsonSchema = openApiParserService.convertSchemaToJsonSchema(responseSchema, openAPI);
                    
                    ValidationResult env1Validation = jsonSchemaValidationService.validateWithCustomChecks(
                            request.getEnv1ResponseBody(), jsonSchema);
                    env1Validation.setPath(request.getPath());
                    env1Validation.setMethod(request.getMethod());
                    env1Validation.setStatusCode(request.getStatusCode());
                    result.setEnv1Validation(env1Validation);
                    
                    ValidationResult env2Validation = jsonSchemaValidationService.validateWithCustomChecks(
                            request.getEnv2ResponseBody(), jsonSchema);
                    env2Validation.setPath(request.getPath());
                    env2Validation.setMethod(request.getMethod());
                    env2Validation.setStatusCode(request.getStatusCode());
                    result.setEnv2Validation(env2Validation);
                } catch (Exception ignored) {
                }
            }
            
            return ResponseEntity.ok(result);
        } catch (Exception e) {
            Map<String, String> error = new HashMap<>();
            error.put("error", e.getMessage());
            return ResponseEntity.badRequest().body(error);
        }
    }

    @PostMapping("/compare/report")
    public ResponseEntity<?> generateComparisonReport(@RequestBody ComparisonRequest request) {
        try {
            ComparisonResult comparisonResult = responseComparisonService.compare(
                    request.getEnv1Name(),
                    request.getEnv2Name(),
                    request.getEnv1ResponseBody(),
                    request.getEnv2ResponseBody()
            );
            
            comparisonResult.setPath(request.getPath());
            comparisonResult.setMethod(request.getMethod());
            
            if (request.getOpenApiSpec() != null && !request.getOpenApiSpec().isEmpty()) {
                try {
                    OpenAPI openAPI = openApiParserService.parseOpenApiSpec(request.getOpenApiSpec());
                    Schema<?> responseSchema = openApiParserService.extractResponseSchema(
                            openAPI, request.getPath(), request.getMethod(), request.getStatusCode());
                    JsonNode jsonSchema = openApiParserService.convertSchemaToJsonSchema(responseSchema, openAPI);
                    
                    ValidationResult env1Validation = streamingValidationService.validateStreaming(
                            request.getEnv1ResponseBody(), jsonSchema);
                    env1Validation.setPath(request.getPath());
                    env1Validation.setMethod(request.getMethod());
                    env1Validation.setStatusCode(request.getStatusCode());
                    comparisonResult.setEnv1Validation(env1Validation);
                    
                    ValidationResult env2Validation = streamingValidationService.validateStreaming(
                            request.getEnv2ResponseBody(), jsonSchema);
                    env2Validation.setPath(request.getPath());
                    env2Validation.setMethod(request.getMethod());
                    env2Validation.setStatusCode(request.getStatusCode());
                    comparisonResult.setEnv2Validation(env2Validation);
                } catch (Exception ignored) {
                }
            }
            
            Map<String, Object> report = responseComparisonService.generateComparisonReport(comparisonResult);
            return ResponseEntity.ok(report);
        } catch (Exception e) {
            Map<String, String> error = new HashMap<>();
            error.put("error", e.getMessage());
            return ResponseEntity.badRequest().body(error);
        }
    }

    @PostMapping("/validate/streaming")
    public ResponseEntity<?> validateStreaming(@RequestBody ValidationRequest request) {
        try {
            OpenAPI openAPI = openApiParserService.parseOpenApiSpec(request.getOpenApiSpec());
            Schema<?> responseSchema = openApiParserService.extractResponseSchema(
                    openAPI, request.getPath(), request.getMethod(), request.getStatusCode());
            
            JsonNode jsonSchema = openApiParserService.convertSchemaToJsonSchema(responseSchema, openAPI);
            ValidationResult result = streamingValidationService.validateStreaming(
                    request.getResponseBody(), jsonSchema);
            
            result.setPath(request.getPath());
            result.setMethod(request.getMethod());
            result.setStatusCode(request.getStatusCode());
            
            return ResponseEntity.ok(result);
        } catch (Exception e) {
            ValidationResult result = new ValidationResult();
            result.setValid(false);
            result.addError("", "校验错误: " + e.getMessage(), 
                    ValidationResult.ErrorType.SCHEMA_ERROR, ValidationResult.Severity.HIGH);
            return ResponseEntity.badRequest().body(result);
        }
    }

    @PostMapping(value = "/validate/junit", produces = MediaType.APPLICATION_XML_VALUE)
    public ResponseEntity<String> generateValidationJUnitReport(@RequestBody ValidationRequest request) {
        try {
            OpenAPI openAPI = openApiParserService.parseOpenApiSpec(request.getOpenApiSpec());
            Schema<?> responseSchema = openApiParserService.extractResponseSchema(
                    openAPI, request.getPath(), request.getMethod(), request.getStatusCode());
            
            JsonNode jsonSchema = openApiParserService.convertSchemaToJsonSchema(responseSchema, openAPI);
            ValidationResult result = streamingValidationService.validateStreaming(
                    request.getResponseBody(), jsonSchema);
            
            result.setPath(request.getPath());
            result.setMethod(request.getMethod());
            result.setStatusCode(request.getStatusCode());
            
            String junitXml = reportGenerationService.generateJUnitXmlReport(result);
            
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(new MediaType("application", "xml", StandardCharsets.UTF_8));
            headers.setContentDispositionFormData("attachment", 
                "validation-report-" + System.currentTimeMillis() + ".xml");
            
            return ResponseEntity.ok()
                    .headers(headers)
                    .body(junitXml);
        } catch (Exception e) {
            ValidationResult result = new ValidationResult();
            result.setValid(false);
            result.addError("", "校验错误: " + e.getMessage(), 
                    ValidationResult.ErrorType.SCHEMA_ERROR, ValidationResult.Severity.HIGH);
            String errorXml = reportGenerationService.generateJUnitXmlReport(result);
            return ResponseEntity.badRequest().body(errorXml);
        }
    }

    @PostMapping(value = "/compare/junit", produces = MediaType.APPLICATION_XML_VALUE)
    public ResponseEntity<String> generateComparisonJUnitReport(@RequestBody ComparisonRequest request) {
        try {
            ComparisonResult comparisonResult = responseComparisonService.compare(
                    request.getEnv1Name(),
                    request.getEnv2Name(),
                    request.getEnv1ResponseBody(),
                    request.getEnv2ResponseBody()
            );
            
            comparisonResult.setPath(request.getPath());
            comparisonResult.setMethod(request.getMethod());
            
            if (request.getOpenApiSpec() != null && !request.getOpenApiSpec().isEmpty()) {
                try {
                    OpenAPI openAPI = openApiParserService.parseOpenApiSpec(request.getOpenApiSpec());
                    Schema<?> responseSchema = openApiParserService.extractResponseSchema(
                            openAPI, request.getPath(), request.getMethod(), request.getStatusCode());
                    JsonNode jsonSchema = openApiParserService.convertSchemaToJsonSchema(responseSchema, openAPI);
                    
                    ValidationResult env1Validation = streamingValidationService.validateStreaming(
                            request.getEnv1ResponseBody(), jsonSchema);
                    comparisonResult.setEnv1Validation(env1Validation);
                    
                    ValidationResult env2Validation = streamingValidationService.validateStreaming(
                            request.getEnv2ResponseBody(), jsonSchema);
                    comparisonResult.setEnv2Validation(env2Validation);
                } catch (Exception ignored) {
                }
            }
            
            String junitXml = reportGenerationService.generateJUnitXmlReport(comparisonResult);
            
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(new MediaType("application", "xml", StandardCharsets.UTF_8));
            headers.setContentDispositionFormData("attachment", 
                "comparison-report-" + System.currentTimeMillis() + ".xml");
            
            return ResponseEntity.ok()
                    .headers(headers)
                    .body(junitXml);
        } catch (Exception e) {
            ComparisonResult errorResult = new ComparisonResult();
            errorResult.addDifference(new ComparisonResult.Difference(
                    "", ComparisonResult.DifferenceType.STRUCTURE_MISMATCH, 
                    ComparisonResult.Severity.CRITICAL, null, null, e.getMessage()));
            String errorXml = reportGenerationService.generateJUnitXmlReport(errorResult);
            return ResponseEntity.badRequest().body(errorXml);
        }
    }

    @PostMapping("/compare/report/enhanced")
    public ResponseEntity<?> generateEnhancedComparisonReport(@RequestBody ComparisonRequest request) {
        try {
            ComparisonResult comparisonResult = responseComparisonService.compare(
                    request.getEnv1Name(),
                    request.getEnv2Name(),
                    request.getEnv1ResponseBody(),
                    request.getEnv2ResponseBody()
            );
            
            comparisonResult.setPath(request.getPath());
            comparisonResult.setMethod(request.getMethod());
            
            if (request.getOpenApiSpec() != null && !request.getOpenApiSpec().isEmpty()) {
                try {
                    OpenAPI openAPI = openApiParserService.parseOpenApiSpec(request.getOpenApiSpec());
                    Schema<?> responseSchema = openApiParserService.extractResponseSchema(
                            openAPI, request.getPath(), request.getMethod(), request.getStatusCode());
                    JsonNode jsonSchema = openApiParserService.convertSchemaToJsonSchema(responseSchema, openAPI);
                    
                    ValidationResult env1Validation = streamingValidationService.validateStreaming(
                            request.getEnv1ResponseBody(), jsonSchema);
                    comparisonResult.setEnv1Validation(env1Validation);
                    
                    ValidationResult env2Validation = streamingValidationService.validateStreaming(
                            request.getEnv2ResponseBody(), jsonSchema);
                    comparisonResult.setEnv2Validation(env2Validation);
                } catch (Exception ignored) {
                }
            }
            
            Map<String, Object> report = reportGenerationService.generateEnhancedJsonReport(comparisonResult);
            return ResponseEntity.ok(report);
        } catch (Exception e) {
            Map<String, String> error = new HashMap<>();
            error.put("error", e.getMessage());
            return ResponseEntity.badRequest().body(error);
        }
    }

    @PostMapping("/mock/generate")
    public ResponseEntity<?> generateMock(@RequestBody ValidationRequest request) {
        try {
            OpenAPI openAPI = openApiParserService.parseOpenApiSpec(request.getOpenApiSpec());
            Schema<?> responseSchema = openApiParserService.extractResponseSchema(
                    openAPI, request.getPath(), request.getMethod(), request.getStatusCode());

            JsonNode jsonSchema = openApiParserService.convertSchemaToJsonSchema(responseSchema, openAPI);
            MockGenerationResult result = mockGenerationService.generateMock(
                    jsonSchema, request.getPath(), request.getMethod(), request.getStatusCode());

            return ResponseEntity.ok(result);
        } catch (Exception e) {
            Map<String, String> error = new HashMap<>();
            error.put("error", "Mock生成失败: " + e.getMessage());
            return ResponseEntity.badRequest().body(error);
        }
    }

    @PostMapping("/compatibility/check")
    public ResponseEntity<?> checkCompatibility(@RequestBody CompatibilityRequest request) {
        try {
            OpenAPI oldOpenAPI = openApiParserService.parseOpenApiSpec(request.getOldOpenApiSpec());
            Schema<?> oldResponseSchema = openApiParserService.extractResponseSchema(
                    oldOpenAPI, request.getPath(), request.getMethod(), request.getStatusCode());
            JsonNode oldJsonSchema = openApiParserService.convertSchemaToJsonSchema(
                    oldResponseSchema, oldOpenAPI);

            OpenAPI newOpenAPI = openApiParserService.parseOpenApiSpec(request.getNewOpenApiSpec());
            Schema<?> newResponseSchema = openApiParserService.extractResponseSchema(
                    newOpenAPI, request.getPath(), request.getMethod(), request.getStatusCode());
            JsonNode newJsonSchema = openApiParserService.convertSchemaToJsonSchema(
                    newResponseSchema, newOpenAPI);

            CompatibilityResult result = versionCompatibilityService.checkCompatibility(
                    oldJsonSchema, newJsonSchema,
                    request.getOldVersion(), request.getNewVersion(),
                    request.getPath(), request.getMethod());

            return ResponseEntity.ok(result);
        } catch (Exception e) {
            Map<String, String> error = new HashMap<>();
            error.put("error", "兼容性检查失败: " + e.getMessage());
            return ResponseEntity.badRequest().body(error);
        }
    }

    @PostMapping("/fix/suggest")
    public ResponseEntity<?> suggestFixes(@RequestBody FixRequest request) {
        try {
            OpenAPI openAPI = openApiParserService.parseOpenApiSpec(request.getOpenApiSpec());
            Schema<?> responseSchema = openApiParserService.extractResponseSchema(
                    openAPI, request.getPath(), request.getMethod(), request.getStatusCode());

            JsonNode jsonSchema = openApiParserService.convertSchemaToJsonSchema(responseSchema, openAPI);
            ValidationResult validationResult = streamingValidationService.validateStreaming(
                    request.getResponseBody(), jsonSchema);

            List<FixSuggestion> suggestions = fixSuggestionService.generateFixSuggestions(
                    validationResult, request.getResponseBody(), jsonSchema);

            Map<String, Object> result = new HashMap<>();
            result.put("valid", validationResult.isValid());
            result.put("errors", validationResult.getErrors());
            result.put("suggestions", suggestions);

            if (request.isAutoFix() && !validationResult.isValid()) {
                String fixedResponse = fixSuggestionService.generateFixedResponse(
                        request.getResponseBody(), suggestions, jsonSchema);
                result.put("fixedResponse", fixedResponse);
            }

            return ResponseEntity.ok(result);
        } catch (Exception e) {
            Map<String, String> error = new HashMap<>();
            error.put("error", "修复建议生成失败: " + e.getMessage());
            return ResponseEntity.badRequest().body(error);
        }
    }
}
