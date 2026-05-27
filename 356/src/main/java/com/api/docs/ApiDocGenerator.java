package com.api.docs;

import com.api.docs.config.GeneratorConfig;
import com.api.docs.filter.PermissionFilter;
import com.api.docs.generator.ExampleGenerator;
import com.api.docs.generator.MarkdownGenerator;
import com.api.docs.generator.OpenApiGenerator;
import com.api.docs.mock.MockServer;
import com.api.docs.model.ApiInfo;
import com.api.docs.scanner.CodeScanner;
import com.api.docs.server.SwaggerUiServer;
import com.api.docs.version.VersionDiff;
import com.api.docs.version.VersionManager;
import io.swagger.v3.oas.models.OpenAPI;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class ApiDocGenerator {
    private static final Logger logger = LoggerFactory.getLogger(ApiDocGenerator.class);

    private final GeneratorConfig config;
    private final CodeScanner scanner;
    private final OpenApiGenerator openApiGenerator;
    private final MarkdownGenerator markdownGenerator;
    private final VersionManager versionManager;
    private final PermissionFilter permissionFilter;
    private final ExampleGenerator exampleGenerator;
    private final MockServer mockServer;
    private SwaggerUiServer swaggerUiServer;
    private ApiInfo lastApiInfo;

    public ApiDocGenerator(GeneratorConfig config) throws Exception {
        this.config = config;
        this.scanner = new CodeScanner(config);
        this.openApiGenerator = new OpenApiGenerator(config);
        this.markdownGenerator = new MarkdownGenerator(config);
        this.versionManager = config.isEnableVersioning() ? new VersionManager(config) : null;
        this.permissionFilter = config.isEnablePermissionFilter() ? createPermissionFilter(config) : null;
        this.exampleGenerator = null;
        this.mockServer = null;
    }

    private PermissionFilter createPermissionFilter(GeneratorConfig config) {
        if (config.getAllowedRoles().isEmpty()) {
            return new PermissionFilter();
        }
        return new PermissionFilter(
                config.getAllowedRoles(),
                config.getSensitiveTags().isEmpty() ? null : config.getSensitiveTags(),
                config.getSensitivePaths().isEmpty() ? null : config.getSensitivePaths(),
                null,
                config.isHideInternalModels()
        );
    }

    public ApiInfo scanCode() {
        logger.info("开始扫描代码...");
        return scanner.scan();
    }

    public OpenAPI generateOpenAPI(ApiInfo apiInfo) {
        logger.info("开始生成OpenAPI文档...");
        return openApiGenerator.generate(apiInfo);
    }

    public void exportOpenAPI(OpenAPI openAPI, String format) throws Exception {
        openApiGenerator.writeOpenAPI(openAPI, config.getOutputPath(), format);
    }

    public void exportMarkdown(ApiInfo apiInfo) throws Exception {
        if (config.isGenerateMarkdown()) {
            logger.info("开始生成Markdown文档...");
            markdownGenerator.writeMarkdown(apiInfo, config.getOutputPath());
        }
    }

    public void saveVersion(OpenAPI openAPI, String version) throws Exception {
        if (versionManager != null) {
            versionManager.saveVersion(openAPI, version);
        }
    }

    public VersionDiff compareVersions(String v1, String v2) throws Exception {
        if (versionManager != null) {
            return versionManager.compareVersions(v1, v2);
        }
        throw new IllegalStateException("版本管理未启用");
    }

    public void generateDiffReport(String v1, String v2) throws Exception {
        if (versionManager != null) {
            VersionDiff diff = versionManager.compareVersions(v1, v2);
            versionManager.saveDiffReport(diff, config.getOutputPath());
            logger.info("差异报告:\n{}", versionManager.generateDiffReport(diff));
        }
    }

    public void startSwaggerUI(OpenAPI openAPI) {
        if (config.isEnableSwaggerUI()) {
            logger.info("启动Swagger UI服务器...");
            swaggerUiServer = new SwaggerUiServer(config);
            swaggerUiServer.start(openAPI);
        }
    }

    public void stopSwaggerUI() {
        if (swaggerUiServer != null) {
            swaggerUiServer.stop();
        }
    }

    public void generateExamples(ApiInfo apiInfo) {
        if (config.isEnableExampleGenerator()) {
            logger.info("开始生成API请求/响应示例");
            ExampleGenerator generator = new ExampleGenerator(apiInfo.getModels());
            generator.generateForApi(apiInfo);
            logger.info("API示例生成完成");
        }
    }

    public void startMockServer(ApiInfo apiInfo) {
        if (config.isEnableMockServer()) {
            logger.info("启动Mock服务...");
            MockServer mock = new MockServer(apiInfo, config.getMockServerPort());
            mock.setEnabled(true);
            mock.start();
        }
    }

    public void stopMockServer() {
        if (mockServer != null) {
            mockServer.stop();
        }
    }

    public ApiInfo applyPermissionFilter(ApiInfo apiInfo) {
        if (permissionFilter != null) {
            return permissionFilter.filterApiInfo(apiInfo);
        }
        return apiInfo;
    }

    public OpenAPI applyPermissionFilter(OpenAPI openAPI) {
        if (permissionFilter != null) {
            return permissionFilter.filterOpenAPI(openAPI);
        }
        return openAPI;
    }

    public void generateAll() throws Exception {
        ApiInfo apiInfo = scanCode();
        lastApiInfo = apiInfo;

        if (config.isEnableExampleGenerator()) {
            generateExamples(apiInfo);
        }

        OpenAPI openAPI = generateOpenAPI(apiInfo);

        exportOpenAPI(openAPI, "json");
        exportOpenAPI(openAPI, "yaml");
        exportMarkdown(apiInfo);

        if (config.isEnablePermissionFilter()) {
            ApiInfo filteredApiInfo = applyPermissionFilter(apiInfo);
            OpenAPI filteredOpenAPI = applyPermissionFilter(openAPI);

            String filteredOutputPath = config.getOutputPath() + "/filtered";
            openApiGenerator.writeOpenAPI(filteredOpenAPI, filteredOutputPath, "json");
            openApiGenerator.writeOpenAPI(filteredOpenAPI, filteredOutputPath, "yaml");
            markdownGenerator.writeMarkdown(filteredApiInfo, filteredOutputPath);
            logger.info("权限过滤后的文档已输出至: {}", filteredOutputPath);
        }

        if (config.isEnableVersioning()) {
            saveVersion(openAPI, config.getApiVersion());
        }

        logger.info("文档生成完成！输出目录: {}", config.getOutputPath());
    }

    public void generateAndServe() throws Exception {
        ApiInfo apiInfo = scanCode();
        lastApiInfo = apiInfo;

        if (config.isEnableExampleGenerator()) {
            generateExamples(apiInfo);
        }

        OpenAPI openAPI = generateOpenAPI(apiInfo);

        exportOpenAPI(openAPI, "json");
        exportOpenAPI(openAPI, "yaml");
        exportMarkdown(apiInfo);

        if (config.isEnableVersioning()) {
            saveVersion(openAPI, config.getApiVersion());
        }

        if (config.isEnableMockServer()) {
            startMockServer(apiInfo);
        }

        if (config.isEnableSwaggerUI()) {
            OpenAPI serveOpenAPI = openAPI;
            if (config.isEnablePermissionFilter()) {
                serveOpenAPI = applyPermissionFilter(openAPI);
            }
            startSwaggerUI(serveOpenAPI);
        }

        logger.info("文档生成完成！输出目录: {}", config.getOutputPath());
    }

    public static void main(String[] args) {
        try {
            if (args.length < 1) {
                printUsage();
                return;
            }

            String command = args[0];
            GeneratorConfig config = parseArgs(args);

            ApiDocGenerator generator = new ApiDocGenerator(config);

            switch (command.toLowerCase()) {
                case "generate":
                    generator.generateAll();
                    break;
                case "serve":
                    generator.generateAndServe();
                    logger.info("服务器运行中，按 Ctrl+C 停止...");
                    Thread.currentThread().join();
                    break;
                case "diff":
                    if (args.length < 3) {
                        System.err.println("diff命令需要两个版本号参数");
                        printUsage();
                        return;
                    }
                    generator.generateDiffReport(args[1], args[2]);
                    break;
                case "scan":
                    ApiInfo apiInfo = generator.scanCode();
                    logger.info("扫描结果: {} 个Controller, {} 个Model",
                            apiInfo.getControllers().size(),
                            apiInfo.getModels().size());
                    break;
                default:
                    printUsage();
            }
        } catch (Exception e) {
            logger.error("执行失败", e);
            System.exit(1);
        }
    }

    private static GeneratorConfig parseArgs(String[] args) {
        GeneratorConfig config = new GeneratorConfig();

        for (int i = 1; i < args.length; i++) {
            String arg = args[i];
            if (arg.startsWith("--project=")) {
                config.setProjectPath(arg.substring(10));
            } else if (arg.startsWith("--output=")) {
                config.setOutputPath(arg.substring(9));
            } else if (arg.startsWith("--version=")) {
                config.setApiVersion(arg.substring(10));
            } else if (arg.startsWith("--title=")) {
                config.setApiTitle(arg.substring(8));
            } else if (arg.startsWith("--server=")) {
                config.setServerUrl(arg.substring(9));
            } else if (arg.startsWith("--port=")) {
                config.setServerPort(Integer.parseInt(arg.substring(7)));
            } else if ("--no-ui".equals(arg)) {
                config.setEnableSwaggerUI(false);
            } else if ("--no-md".equals(arg)) {
                config.setGenerateMarkdown(false);
            } else if ("--enable-filter".equals(arg)) {
                config.setEnablePermissionFilter(true);
            } else if (arg.startsWith("--role=")) {
                config.setEnablePermissionFilter(true);
                config.addAllowedRole(arg.substring(7));
            } else if (arg.startsWith("--sensitive-tag=")) {
                config.addSensitiveTag(arg.substring(15));
            } else if (arg.startsWith("--sensitive-path=")) {
                config.addSensitivePath(arg.substring(16));
            } else if ("--show-internal-models".equals(arg)) {
                config.setHideInternalModels(false);
            } else if ("--no-examples".equals(arg)) {
                config.setEnableExampleGenerator(false);
            } else if ("--enable-mock".equals(arg)) {
                config.setEnableMockServer(true);
            } else if (arg.startsWith("--mock-port=")) {
                config.setEnableMockServer(true);
                config.setMockServerPort(Integer.parseInt(arg.substring(12)));
            } else if ("--no-annotations".equals(arg)) {
                config.setEnableCustomAnnotations(false);
            }
        }

        if (config.getProjectPath() == null || config.getProjectPath().isEmpty()) {
            config.setProjectPath(".");
        }

        return config;
    }

    private static void printUsage() {
        System.out.println("API文档自动生成工具");
        System.out.println();
        System.out.println("用法:");
        System.out.println("  java -jar api-doc-generator.jar <command> [options]");
        System.out.println();
        System.out.println("命令:");
        System.out.println("  generate    生成API文档 (JSON/YAML/Markdown)");
        System.out.println("  serve       生成文档并启动Swagger UI服务器");
        System.out.println("  diff <v1> <v2>  对比两个版本的API差异");
        System.out.println("  scan        仅扫描代码并显示统计");
        System.out.println();
        System.out.println("基础选项:");
        System.out.println("  --project=<path>    Spring Boot项目路径 (默认: 当前目录)");
        System.out.println("  --output=<path>     输出目录 (默认: ./docs)");
        System.out.println("  --version=<ver>     API版本号 (默认: 1.0.0)");
        System.out.println("  --title=<title>     API标题 (默认: API Documentation)");
        System.out.println("  --server=<url>      服务器地址 (默认: http://localhost:8080)");
        System.out.println("  --port=<port>       Swagger UI端口 (默认: 8088)");
        System.out.println("  --no-ui             禁用Swagger UI");
        System.out.println("  --no-md             禁用Markdown导出");
        System.out.println();
        System.out.println("权限过滤选项:");
        System.out.println("  --enable-filter     启用权限过滤");
        System.out.println("  --role=<role>       用户角色 (ADMIN/DEVELOPER/USER/GUEST)，可多次指定");
        System.out.println("  --sensitive-tag=<tag>   敏感标签，可多次指定");
        System.out.println("  --sensitive-path=<path> 敏感路径前缀，可多次指定");
        System.out.println("  --show-internal-models  显示内部模型");
        System.out.println();
        System.out.println("示例和Mock选项:");
        System.out.println("  --no-examples       禁用自动生成请求/响应示例");
        System.out.println("  --enable-mock       启用Mock服务");
        System.out.println("  --mock-port=<port>  Mock服务端口 (默认: 8089)");
        System.out.println("  --no-annotations    禁用自定义注解解析");
        System.out.println();
        System.out.println("示例:");
        System.out.println("  java -jar api-doc-generator.jar generate --project=../my-spring-boot-app");
        System.out.println("  java -jar api-doc-generator.jar serve --project=../my-app --port=9000");
        System.out.println("  java -jar api-doc-generator.jar diff 1.0.0 1.1.0");
        System.out.println("  java -jar api-doc-generator.jar generate --enable-filter --role=USER");
        System.out.println("  java -jar api-doc-generator.jar serve --enable-mock --mock-port=8090");
        System.out.println("  java -jar api-doc-generator.jar serve --enable-filter --role=USER --sensitive-path=/api/admin");
    }
}