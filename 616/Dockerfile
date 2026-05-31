FROM eclipse-temurin:17-jre

WORKDIR /app

COPY dlq-api/target/dlq-api-1.0.0.jar /app/dlq-api-1.0.0.jar

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/actuator/health || exit 1

ENTRYPOINT ["java", "-jar", "dlq-api-1.0.0.jar"]
