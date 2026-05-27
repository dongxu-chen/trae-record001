package com.api.docs.generator;

import com.api.docs.config.GeneratorConfig;
import com.api.docs.model.*;
import freemarker.template.Configuration;
import freemarker.template.Template;
import freemarker.template.TemplateException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.io.StringWriter;
import java.util.*;

public class MarkdownGenerator {
    private static final Logger logger = LoggerFactory.getLogger(MarkdownGenerator.class);
    private final GeneratorConfig config;
    private final Configuration freemarkerConfig;

    public MarkdownGenerator(GeneratorConfig config) throws IOException {
        this.config = config;
        this.freemarkerConfig = new Configuration(Configuration.VERSION_2_3_32);
        this.freemarkerConfig.setClassForTemplateLoading(MarkdownGenerator.class, "/templates");
        this.freemarkerConfig.setDefaultEncoding("UTF-8");
    }

    public String generate(ApiInfo apiInfo) throws IOException, TemplateException {
        logger.info("开始生成Markdown文档");

        Map<String, Object> dataModel = new HashMap<>();
        dataModel.put("title", apiInfo.getTitle());
        dataModel.put("description", apiInfo.getDescription());
        dataModel.put("version", apiInfo.getVersion());
        dataModel.put("serverUrl", apiInfo.getServerUrl());
        dataModel.put("generatedAt", new Date().toString());

        List<Map<String, Object>> controllersData = new ArrayList<>();
        for (ControllerInfo controller : apiInfo.getControllers()) {
            Map<String, Object> controllerData = new HashMap<>();
            controllerData.put("className", controller.getClassName());
            controllerData.put("basePath", controller.getBasePath());
            controllerData.put("description", controller.getDescription());

            List<Map<String, Object>> methodsData = new ArrayList<>();
            for (MethodInfo method : controller.getMethods()) {
                Map<String, Object> methodData = new HashMap<>();
                methodData.put("name", method.getName());
                methodData.put("httpMethod", method.getHttpMethod());
                methodData.put("path", method.getPath());
                methodData.put("summary", method.getSummary());
                methodData.put("description", method.getDescription());
                methodData.put("deprecated", method.isDeprecated());
                methodData.put("requestBodyType", method.getRequestBodyType());
                methodData.put("responseType", method.getResponseType());

                List<Map<String, Object>> paramsData = new ArrayList<>();
                for (ParameterInfo param : method.getParameters()) {
                    Map<String, Object> paramData = new HashMap<>();
                    paramData.put("name", param.getName());
                    paramData.put("type", param.getType());
                    paramData.put("description", param.getDescription());
                    paramData.put("in", param.getIn());
                    paramData.put("required", param.isRequired());
                    paramData.put("defaultValue", param.getDefaultValue());
                    paramsData.add(paramData);
                }
                methodData.put("parameters", paramsData);
                methodsData.add(methodData);
            }
            controllerData.put("methods", methodsData);
            controllersData.add(controllerData);
        }
        dataModel.put("controllers", controllersData);

        List<Map<String, Object>> modelsData = new ArrayList<>();
        for (ModelInfo model : apiInfo.getModels()) {
            Map<String, Object> modelData = new HashMap<>();
            modelData.put("className", model.getClassName());
            modelData.put("description", model.getDescription());

            List<Map<String, Object>> fieldsData = new ArrayList<>();
            for (FieldInfo field : model.getFields()) {
                Map<String, Object> fieldData = new HashMap<>();
                fieldData.put("name", field.getName());
                fieldData.put("type", field.getType());
                fieldData.put("description", field.getDescription());
                fieldData.put("required", field.isRequired());
                fieldData.put("example", field.getExample());
                fieldsData.add(fieldData);
            }
            modelData.put("fields", fieldsData);
            modelsData.add(modelData);
        }
        dataModel.put("models", modelsData);

        Template template = freemarkerConfig.getTemplate("api-docs.ftl");
        StringWriter writer = new StringWriter();
        template.process(dataModel, writer);

        logger.info("Markdown文档生成完成");
        return writer.toString();
    }

    public void writeMarkdown(ApiInfo apiInfo, String outputPath) throws IOException, TemplateException {
        File outputDir = new File(outputPath);
        if (!outputDir.exists()) {
            outputDir.mkdirs();
        }

        String content = generate(apiInfo);
        File outputFile = new File(outputDir, "api-docs.md");
        try (FileWriter writer = new FileWriter(outputFile)) {
            writer.write(content);
        }

        logger.info("Markdown文档已写入: {}", outputFile.getAbsolutePath());
    }
}