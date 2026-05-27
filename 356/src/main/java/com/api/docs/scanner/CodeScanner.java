package com.api.docs.scanner;

import com.api.docs.config.GeneratorConfig;
import com.api.docs.model.*;
import com.github.javaparser.JavaParser;
import com.github.javaparser.ParseResult;
import com.github.javaparser.ast.CompilationUnit;
import com.github.javaparser.ast.body.ClassOrInterfaceDeclaration;
import com.github.javaparser.ast.body.FieldDeclaration;
import com.github.javaparser.ast.body.MethodDeclaration;
import com.github.javaparser.ast.body.Parameter;
import com.github.javaparser.ast.expr.AnnotationExpr;
import com.github.javaparser.ast.expr.MemberValuePair;
import com.github.javaparser.ast.expr.NormalAnnotationExpr;
import com.github.javaparser.ast.expr.SingleMemberAnnotationExpr;
import com.github.javaparser.ast.type.Type;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.*;
import java.util.stream.Stream;

public class CodeScanner {
    private static final Logger logger = LoggerFactory.getLogger(CodeScanner.class);
    private final GeneratorConfig config;
    private final JavaParser javaParser;
    private final Set<String> processedClasses = new HashSet<>();
    private final Map<String, ModelInfo> models = new HashMap<>();

    private static final Set<String> CONTROLLER_ANNOTATIONS = new HashSet<>(Arrays.asList(
            "RestController", "Controller", "RequestMapping"
    ));

    private static final Set<String> HTTP_METHOD_ANNOTATIONS = new HashSet<>(Arrays.asList(
            "GetMapping", "PostMapping", "PutMapping", "DeleteMapping",
            "PatchMapping", "RequestMapping"
    ));

    private static final Set<String> PARAM_ANNOTATIONS = new HashSet<>(Arrays.asList(
            "RequestParam", "PathVariable", "RequestBody", "RequestHeader"
    ));

    public CodeScanner(GeneratorConfig config) {
        this.config = config;
        this.javaParser = new JavaParser();
    }

    public ApiInfo scan() {
        logger.info("开始扫描项目: {}", config.getProjectPath());
        ApiInfo apiInfo = new ApiInfo();
        apiInfo.setTitle(config.getApiTitle());
        apiInfo.setDescription(config.getApiDescription());
        apiInfo.setVersion(config.getApiVersion());
        apiInfo.setServerUrl(config.getServerUrl());

        List<File> javaFiles = findJavaFiles(config.getProjectPath());
        logger.info("找到 {} 个Java文件", javaFiles.size());

        for (File javaFile : javaFiles) {
            try {
                parseJavaFile(javaFile, apiInfo);
            } catch (Exception e) {
                logger.error("解析文件失败: {}", javaFile.getPath(), e);
            }
        }

        apiInfo.setModels(new ArrayList<>(models.values()));
        logger.info("扫描完成: {} 个Controller, {} 个Model",
                apiInfo.getControllers().size(), apiInfo.getModels().size());
        return apiInfo;
    }

    private List<File> findJavaFiles(String projectPath) {
        List<File> javaFiles = new ArrayList<>();
        try (Stream<Path> paths = Files.walk(Paths.get(projectPath))) {
            paths.filter(Files::isRegularFile)
                    .filter(p -> p.toString().endsWith(".java"))
                    .filter(p -> !p.toString().contains("target"))
                    .filter(p -> !p.toString().contains(".git"))
                    .forEach(p -> javaFiles.add(p.toFile()));
        } catch (IOException e) {
            logger.error("遍历文件失败", e);
        }
        return javaFiles;
    }

    private void parseJavaFile(File javaFile, ApiInfo apiInfo) throws IOException {
        FileInputStream in = new FileInputStream(javaFile);
        ParseResult<CompilationUnit> result = javaParser.parse(in);

        if (result.isSuccessful() && result.getResult().isPresent()) {
            CompilationUnit cu = result.getResult().get();

            Optional<ClassOrInterfaceDeclaration> classOpt = cu.getClassByName(
                    javaFile.getName().replace(".java", "")
            );

            if (classOpt.isPresent()) {
                ClassOrInterfaceDeclaration clazz = classOpt.get();
                String packageName = cu.getPackageDeclaration()
                        .map(pd -> pd.getNameAsString())
                        .orElse("");

                if (isControllerClass(clazz)) {
                    ControllerInfo controller = parseController(clazz, packageName);
                    apiInfo.addController(controller);
                    logger.debug("解析Controller: {}.{}", packageName, clazz.getNameAsString());
                } else if (isModelClass(clazz)) {
                    ModelInfo model = parseModel(clazz, packageName);
                    models.put(model.getClassName(), model);
                    logger.debug("解析Model: {}.{}", packageName, clazz.getNameAsString());
                }
            }
        }
        in.close();
    }

    private boolean isControllerClass(ClassOrInterfaceDeclaration clazz) {
        return clazz.getAnnotations().stream()
                .anyMatch(a -> CONTROLLER_ANNOTATIONS.contains(a.getNameAsString()));
    }

    private boolean isModelClass(ClassOrInterfaceDeclaration clazz) {
        String className = clazz.getNameAsString();
        return className.endsWith("DTO") || className.endsWith("Vo") ||
                className.endsWith("Request") || className.endsWith("Response") ||
                className.endsWith("Req") || className.endsWith("Res");
    }

    private ControllerInfo parseController(ClassOrInterfaceDeclaration clazz, String packageName) {
        ControllerInfo controller = new ControllerInfo();
        controller.setClassName(clazz.getNameAsString());
        controller.setPackageName(packageName);
        controller.setBasePath(getAnnotationValue(clazz, "RequestMapping", "value", ""));

        String description = getClassJavadocDescription(clazz);
        if (description.isEmpty()) {
            description = getAnnotationValue(clazz, "Api", "tags", clazz.getNameAsString());
        }
        controller.setDescription(description);

        for (MethodDeclaration method : clazz.getMethods()) {
            if (isApiMethod(method)) {
                MethodInfo methodInfo = parseMethod(method, controller.getBasePath());
                methodInfo.addTag(controller.getClassName());
                controller.addMethod(methodInfo);
            }
        }

        return controller;
    }

    private boolean isApiMethod(MethodDeclaration method) {
        return method.getAnnotations().stream()
                .anyMatch(a -> HTTP_METHOD_ANNOTATIONS.contains(a.getNameAsString()));
    }

    private MethodInfo parseMethod(MethodDeclaration method, String basePath) {
        MethodInfo methodInfo = new MethodInfo();
        methodInfo.setName(method.getNameAsString());

        String httpMethod = "GET";
        String path = "";

        for (AnnotationExpr annotation : method.getAnnotations()) {
            String annoName = annotation.getNameAsString();
            if (HTTP_METHOD_ANNOTATIONS.contains(annoName)) {
                if (annoName.equals("RequestMapping")) {
                    httpMethod = getAnnotationValue(method, "RequestMapping", "method", "GET")
                            .replace("RequestMethod.", "");
                    path = getAnnotationValue(method, "RequestMapping", "value", "");
                } else {
                    httpMethod = annoName.replace("Mapping", "").toUpperCase();
                    path = getAnnotationValue(method, annoName, "value", "");
                }
                break;
            }
        }

        methodInfo.setHttpMethod(httpMethod);
        methodInfo.setPath(combinePath(basePath, path));

        methodInfo.setSummary(getMethodJavadocSummary(method));
        methodInfo.setDescription(getMethodJavadocDescription(method));
        methodInfo.setDeprecated(method.isAnnotationPresent("Deprecated"));

        for (Parameter parameter : method.getParameters()) {
            String paramType = parameter.getTypeAsString();
            if (parameter.isAnnotationPresent("RequestBody")) {
                methodInfo.setRequestBodyType(paramType);
                queueModelForParsing(paramType);
            } else {
                ParameterInfo paramInfo = parseParameter(parameter);
                if (paramInfo != null) {
                    methodInfo.addParameter(paramInfo);
                }
            }
        }

        String returnType = method.getTypeAsString();
        methodInfo.setResponseType(returnType);
        queueModelForParsing(returnType);

        return methodInfo;
    }

    private ParameterInfo parseParameter(Parameter parameter) {
        ParameterInfo paramInfo = new ParameterInfo();
        paramInfo.setName(parameter.getNameAsString());
        paramInfo.setType(parameter.getTypeAsString());
        paramInfo.setRequired(false);
        paramInfo.setIn("query");

        if (parameter.isAnnotationPresent("PathVariable")) {
            paramInfo.setIn("path");
            paramInfo.setRequired(true);
            paramInfo.setName(getAnnotationValue(parameter, "PathVariable", "value", paramInfo.getName()));
        } else if (parameter.isAnnotationPresent("RequestParam")) {
            paramInfo.setIn("query");
            paramInfo.setName(getAnnotationValue(parameter, "RequestParam", "value", paramInfo.getName()));
            paramInfo.setRequired(Boolean.parseBoolean(
                    getAnnotationValue(parameter, "RequestParam", "required", "false")
            ));
            paramInfo.setDefaultValue(getAnnotationValue(parameter, "RequestParam", "defaultValue", ""));
        } else if (parameter.isAnnotationPresent("RequestHeader")) {
            paramInfo.setIn("header");
            paramInfo.setName(getAnnotationValue(parameter, "RequestHeader", "value", paramInfo.getName()));
            paramInfo.setRequired(Boolean.parseBoolean(
                    getAnnotationValue(parameter, "RequestHeader", "required", "false")
            ));
        } else {
            return null;
        }

        return paramInfo;
    }

    private ModelInfo parseModel(ClassOrInterfaceDeclaration clazz, String packageName) {
        String className = clazz.getNameAsString();
        if (processedClasses.contains(className)) {
            return models.get(className);
        }
        processedClasses.add(className);

        ModelInfo model = new ModelInfo();
        model.setClassName(className);
        model.setPackageName(packageName);
        model.setDescription(getClassJavadocDescription(clazz));

        for (FieldDeclaration field : clazz.getFields()) {
            for (com.github.javaparser.ast.body.VariableDeclarator var : field.getVariables()) {
                FieldInfo fieldInfo = new FieldInfo();
                fieldInfo.setName(var.getNameAsString());
                fieldInfo.setType(var.getTypeAsString());
                fieldInfo.setDescription(getFieldJavadocDescription(field));
                fieldInfo.setRequired(field.isAnnotationPresent("NotNull") ||
                        field.isAnnotationPresent("NonNull") ||
                        field.isAnnotationPresent("NotEmpty"));
                fieldInfo.setDeprecated(field.isAnnotationPresent("Deprecated"));

                model.addField(fieldInfo);
                queueModelForParsing(var.getTypeAsString());
            }
        }

        return model;
    }

    private void queueModelForParsing(String typeName) {
        Set<String> extractedTypes = extractAllTypesRecursively(typeName);
        for (String type : extractedTypes) {
            if (isPrimitiveType(type)) continue;
            if (processedClasses.contains(type)) continue;

            File modelFile = findModelFile(config.getProjectPath(), type);
            if (modelFile != null) {
                try {
                    FileInputStream in = new FileInputStream(modelFile);
                    ParseResult<CompilationUnit> result = javaParser.parse(in);
                    if (result.isSuccessful() && result.getResult().isPresent()) {
                        CompilationUnit cu = result.getResult().get();
                        Optional<ClassOrInterfaceDeclaration> classOpt = cu.getClassByName(type);
                        if (classOpt.isPresent()) {
                            String packageName = cu.getPackageDeclaration()
                                    .map(pd -> pd.getNameAsString())
                                    .orElse("");
                            ModelInfo model = parseModel(classOpt.get(), packageName);
                            models.put(model.getClassName(), model);
                        }
                    }
                    in.close();
                } catch (Exception e) {
                    logger.warn("解析Model失败: {}", type);
                }
            }
        }
    }

    private Set<String> extractAllTypesRecursively(String typeName) {
        Set<String> result = new LinkedHashSet<>();
        extractTypesRecursively(typeName, result, 0);
        return result;
    }

    private void extractTypesRecursively(String typeName, Set<String> result, int depth) {
        if (depth > 10 || typeName == null || typeName.isEmpty()) {
            return;
        }

        typeName = typeName.trim();

        int genericStart = typeName.indexOf('<');
        int genericEnd = typeName.lastIndexOf('>');

        if (genericStart > 0 && genericEnd > genericStart) {
            String outerType = typeName.substring(0, genericStart).trim();
            if (!isPrimitiveType(outerType) && !outerType.isEmpty()) {
                result.add(outerType);
            }

            String genericContent = typeName.substring(genericStart + 1, genericEnd);
            List<String> genericParams = splitGenericParameters(genericContent);
            for (String param : genericParams) {
                extractTypesRecursively(param, result, depth + 1);
            }
        } else {
            String cleanType = typeName.replace("[]", "").trim();
            if (!isPrimitiveType(cleanType) && !cleanType.isEmpty()) {
                result.add(cleanType);
            }
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

    private File findModelFile(String projectPath, String className) {
        try (Stream<Path> paths = Files.walk(Paths.get(projectPath))) {
            return paths.filter(Files::isRegularFile)
                    .filter(p -> p.getFileName().toString().equals(className + ".java"))
                    .findFirst()
                    .map(Path::toFile)
                    .orElse(null);
        } catch (IOException e) {
            return null;
        }
    }

    private boolean isPrimitiveType(String type) {
        Set<String> primitives = new HashSet<>(Arrays.asList(
                "String", "Integer", "int", "Long", "long", "Boolean", "boolean",
                "Double", "double", "Float", "float", "Byte", "byte", "Character", "char",
                "Date", "LocalDate", "LocalDateTime", "BigDecimal", "List", "Set", "Map",
                "void", "Void", "Object"
        ));
        return primitives.contains(type) || type.startsWith("java.");
    }

    private String combinePath(String basePath, String methodPath) {
        if (basePath.isEmpty()) return methodPath.isEmpty() ? "/" : methodPath;
        if (methodPath.isEmpty()) return basePath;
        if (basePath.endsWith("/")) basePath = basePath.substring(0, basePath.length() - 1);
        if (!methodPath.startsWith("/")) methodPath = "/" + methodPath;
        return basePath + methodPath;
    }

    private String getAnnotationValue(ClassOrInterfaceDeclaration clazz, String annotationName, String key, String defaultValue) {
        return clazz.getAnnotationByName(annotationName)
                .map(this::extractAnnotationValue)
                .orElse(defaultValue);
    }

    private String getAnnotationValue(MethodDeclaration method, String annotationName, String key, String defaultValue) {
        return method.getAnnotationByName(annotationName)
                .map(a -> extractAnnotationValue(a, key))
                .orElse(defaultValue);
    }

    private String getAnnotationValue(Parameter parameter, String annotationName, String key, String defaultValue) {
        return parameter.getAnnotationByName(annotationName)
                .map(a -> extractAnnotationValue(a, key))
                .orElse(defaultValue);
    }

    private String extractAnnotationValue(AnnotationExpr expr) {
        if (expr instanceof SingleMemberAnnotationExpr) {
            return removeQuotes(((SingleMemberAnnotationExpr) expr).getMemberValue().toString());
        } else if (expr instanceof NormalAnnotationExpr) {
            return ((NormalAnnotationExpr) expr).getPairs().stream()
                    .findFirst()
                    .map(p -> removeQuotes(p.getValue().toString()))
                    .orElse("");
        }
        return "";
    }

    private String extractAnnotationValue(AnnotationExpr expr, String key) {
        if (expr instanceof SingleMemberAnnotationExpr) {
            return removeQuotes(((SingleMemberAnnotationExpr) expr).getMemberValue().toString());
        } else if (expr instanceof NormalAnnotationExpr) {
            for (MemberValuePair pair : ((NormalAnnotationExpr) expr).getPairs()) {
                if (pair.getNameAsString().equals(key)) {
                    return removeQuotes(pair.getValue().toString());
                }
            }
        }
        return "";
    }

    private String removeQuotes(String value) {
        if (value == null) return "";
        return value.replaceAll("^\"|\"$", "");
    }

    private String getClassJavadocDescription(ClassOrInterfaceDeclaration clazz) {
        return clazz.getJavadoc()
                .map(j -> j.getDescription().toText())
                .map(String::trim)
                .orElse("");
    }

    private String getMethodJavadocSummary(MethodDeclaration method) {
        return method.getJavadoc()
                .map(j -> j.getDescription().toText().split("\n")[0].trim())
                .orElse("");
    }

    private String getMethodJavadocDescription(MethodDeclaration method) {
        return method.getJavadoc()
                .map(j -> j.getDescription().toText().trim())
                .orElse("");
    }

    private String getFieldJavadocDescription(FieldDeclaration field) {
        return field.getJavadoc()
                .map(j -> j.getDescription().toText().trim())
                .orElse("");
    }
}