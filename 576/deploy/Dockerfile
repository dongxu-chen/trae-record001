FROM maven:3.8.6-openjdk-11 AS builder

WORKDIR /app

COPY pom.xml .
COPY lock-core/pom.xml lock-core/
COPY lock-redis/pom.xml lock-redis/
COPY lock-zookeeper/pom.xml lock-zookeeper/
COPY lock-monitor/pom.xml lock-monitor/
COPY lock-analysis/pom.xml lock-analysis/
COPY lock-boot/pom.xml lock-boot/

RUN mvn dependency:go-offline -B

COPY . .

RUN mvn clean package -DskipTests

FROM openjdk:11-jre-slim

WORKDIR /app

COPY --from=builder /app/lock-boot/target/*.jar app.jar

EXPOSE 8080

ENTRYPOINT ["java", "-jar", "app.jar"]