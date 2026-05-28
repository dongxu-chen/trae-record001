FROM maven:3.9-eclipse-temurin-17 AS builder

WORKDIR /app

COPY pom.xml .
COPY mq-monitor-common ./mq-monitor-common
COPY mq-monitor-mq-clients ./mq-monitor-mq-clients
COPY mq-monitor-collector ./mq-monitor-collector
COPY mq-monitor-alert ./mq-monitor-alert
COPY mq-monitor-prediction ./mq-monitor-prediction
COPY mq-monitor-comparison ./mq-monitor-comparison
COPY mq-monitor-exporter ./mq-monitor-api ./mq-monitor-exporter
COPY mq-monitor-api ./mq-monitor-api
COPY mq-monitor-bootstrap ./mq-monitor-bootstrap

RUN mvn clean package -DskipTests

FROM eclipse-temurin:17-jre-slim

WORKDIR /app

COPY --from=builder /app/mq-monitor-bootstrap/target/mq-monitor-bootstrap-1.0.0.jar /app/app.jar

EXPOSE 8080

ENV JAVA_OPTS="-Xms512m -Xmx1024m"

ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar /app/app.jar"]
