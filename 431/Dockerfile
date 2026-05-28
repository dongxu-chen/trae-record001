FROM openjdk:11-jre-slim

LABEL maintainer="rate-limit-center"
LABEL description="Rate Limit Center - Sentinel + Redis + Apollo"

WORKDIR /app

ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

COPY target/rate-limit-center-1.0.0.jar /app/rate-limit-center.jar

EXPOSE 8090 8719 18730

ENV JAVA_OPTS="-Xms512m -Xmx1024m -XX:+UseG1GC -XX:MaxGCPauseMillis=100"

ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar /app/rate-limit-center.jar --spring.profiles.active=${SPRING_PROFILES_ACTIVE:-prod}"]
