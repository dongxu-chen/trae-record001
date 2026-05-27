package com.api.docs.server;

import com.api.docs.config.GeneratorConfig;
import io.swagger.v3.core.util.Json;
import io.swagger.v3.oas.models.OpenAPI;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import spark.Service;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.stream.Collectors;

import static spark.Spark.*;

public class SwaggerUiServer {
    private static final Logger logger = LoggerFactory.getLogger(SwaggerUiServer.class);
    private final GeneratorConfig config;
    private OpenAPI openAPI;
    private Service service;

    public SwaggerUiServer(GeneratorConfig config) {
        this.config = config;
    }

    public void start(OpenAPI openAPI) {
        this.openAPI = openAPI;
        int port = config.getServerPort();

        service = Service.ignite();
        service.port(port);

        service.staticFileLocation("/swagger-ui");

        service.get("/openapi.json", (req, res) -> {
            res.type("application/json");
            return Json.pretty().writeValueAsString(openAPI);
        });

        service.get("/", (req, res) -> {
            res.redirect("/swagger-ui/index.html");
            return null;
        });

        service.awaitInitialization();
        logger.info("Swagger UI服务器已启动: http://localhost:{}/swagger-ui/index.html", port);
        logger.info("OpenAPI JSON: http://localhost:{}/openapi.json", port);
    }

    public void stop() {
        if (service != null) {
            service.stop();
            logger.info("Swagger UI服务器已停止");
        }
    }

    public void waitForStop() {
        try {
            Thread.currentThread().join();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
}