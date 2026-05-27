package com.api.docs.mock;

import com.api.docs.generator.ExampleGenerator;
import com.api.docs.model.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import spark.Service;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class MockServer {
    private static final Logger logger = LoggerFactory.getLogger(MockServer.class);
    private final ApiInfo apiInfo;
    private final ExampleGenerator exampleGenerator;
    private final ObjectMapper objectMapper = new ObjectMapper();
    private Service service;
    private int port;
    private boolean enabled;
    private final Map<String, MethodInfo> routeMap = new HashMap<>();

    public MockServer(ApiInfo apiInfo, int port) {
        this.apiInfo = apiInfo;
        this.port = port;
        this.exampleGenerator = new ExampleGenerator(apiInfo.getModels());
        buildRouteMap();
    }

    private void buildRouteMap() {
        for (ControllerInfo controller : apiInfo.getControllers()) {
            for (MethodInfo method : controller.getMethods()) {
                String key = method.getHttpMethod().toUpperCase() + ":" + convertToSparkPath(method.getPath());
                routeMap.put(key, method);
            }
        }
    }

    private String convertToSparkPath(String path) {
        if (path == null) return "/";
        return path.replaceAll("\\{([^}]+)\\}", ":$1");
    }

    public void setEnabled(boolean enabled) {
        this.enabled = enabled;
    }

    public void start() {
        if (!enabled) {
            logger.info("Mock服务未启用");
            return;
        }

        logger.info("启动Mock服务，端口: {}", port);
        service = Service.ignite();
        service.port(port);

        service.before((request, response) -> {
            response.header("Access-Control-Allow-Origin", "*");
            response.header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, PATCH, OPTIONS");
            response.header("Access-Control-Allow-Headers", "*");
            response.type("application/json");
        });

        service.options("/*", (request, response) -> {
            response.status(200);
            return "";
        });

        service.path("/mock", () -> {
            for (Map.Entry<String, MethodInfo> entry : routeMap.entrySet()) {
                registerRoute(entry.getKey(), entry.getValue());
            }
        });

        service.get("/mock/_routes", (request, response) -> {
            Map<String, Object> result = new HashMap<>();
            result.put("total", routeMap.size());
            result.put("routes", routeMap.keySet());
            return objectMapper.writeValueAsString(result);
        });

        service.awaitInitialization();
        logger.info("Mock服务启动成功: http://localhost:{}", port);
        logger.info("Mock路由数量: {}", routeMap.size());
        logger.info("Mock路由列表: http://localhost:{}/mock/_routes", port);
    }

    private void registerRoute(String routeKey, MethodInfo methodInfo) {
        String[] parts = routeKey.split(":", 2);
        String httpMethod = parts[0];
        String path = parts[1];

        switch (httpMethod) {
            case "GET":
                service.get(path, (request, response) -> handleRequest(methodInfo, request, response));
                break;
            case "POST":
                service.post(path, (request, response) -> handleRequest(methodInfo, request, response));
                break;
            case "PUT":
                service.put(path, (request, response) -> handleRequest(methodInfo, request, response));
                break;
            case "DELETE":
                service.delete(path, (request, response) -> handleRequest(methodInfo, request, response));
                break;
            case "PATCH":
                service.patch(path, (request, response) -> handleRequest(methodInfo, request, response));
                break;
        }
    }

    private String handleRequest(MethodInfo methodInfo,
                                  spark.Request request,
                                  spark.Response response) {
        try {
            Map<String, Object> result = new HashMap<>();
            result.put("success", true);
            result.put("code", 200);
            result.put("message", "Mock Response");
            result.put("mock", true);
            result.put("timestamp", System.currentTimeMillis());
            result.put("method", methodInfo.getHttpMethod());
            result.put("path", methodInfo.getPath());

            Map<String, String> pathParams = new HashMap<>();
            for (String param : request.params()) {
                pathParams.put(param, request.params(param));
            }
            if (!pathParams.isEmpty()) {
                result.put("pathParams", pathParams);
            }

            Map<String, String[]> queryParams = request.queryMap().toMap();
            if (!queryParams.isEmpty()) {
                result.put("queryParams", queryParams);
            }

            String requestBody = request.body();
            if (requestBody != null && !requestBody.isEmpty()) {
                try {
                    result.put("requestBody", objectMapper.readValue(requestBody, Object.class));
                } catch (Exception e) {
                    result.put("requestBody", requestBody);
                }
            }

            if (methodInfo.getResponseExample() != null) {
                result.put("data", methodInfo.getResponseExample());
            } else if (methodInfo.getResponseType() != null && !methodInfo.getResponseType().isEmpty()) {
                Object mockData = exampleGenerator.generateExampleForType(methodInfo.getResponseType());
                if (mockData != null) {
                    result.put("data", mockData);
                }
            }

            if (methodInfo.getResponseExample() == null && methodInfo.getResponseType() != null) {
                methodInfo.setResponseExample(result.get("data"));
            }

            response.status(200);
            return objectMapper.writerWithDefaultPrettyPrinter().writeValueAsString(result);
        } catch (Exception e) {
            logger.error("Mock请求处理失败", e);
            Map<String, Object> error = new HashMap<>();
            error.put("success", false);
            error.put("code", 500);
            error.put("message", "Mock Server Error: " + e.getMessage());
            error.put("mock", true);
            try {
                return objectMapper.writeValueAsString(error);
            } catch (Exception ex) {
                return "{\"success\":false,\"code\":500,\"message\":\"Internal Server Error\"}";
            }
        }
    }

    public void stop() {
        if (service != null) {
            service.stop();
            logger.info("Mock服务已停止");
        }
    }

    public int getPort() {
        return port;
    }

    public void setPort(int port) {
        this.port = port;
    }

    public List<String> getRoutes() {
        return routeMap.keySet().stream().toList();
    }
}
