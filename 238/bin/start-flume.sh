#!/bin/bash
# ============================================
# Flume 日志采集启动脚本
# ============================================

# 配置参数
FLUME_HOME=/opt/flume
AGENT_NAME=a1
CONF_FILE=conf/flume-agent.conf
LOG_DIR=logs
PID_FILE=flume-agent.pid

# 创建日志目录
mkdir -p ${LOG_DIR}

# JVM 参数配置
export JAVA_OPTS="-Xms4g -Xmx8g \
    -XX:+UseG1GC \
    -XX:MaxGCPauseMillis=200 \
    -XX:+HeapDumpOnOutOfMemoryError \
    -XX:HeapDumpPath=${LOG_DIR}/heapdump.hprof \
    -Dcom.sun.management.jmxremote \
    -Dcom.sun.management.jmxremote.port=54321 \
    -Dcom.sun.management.jmxremote.authenticate=false \
    -Dcom.sun.management.jmxremote.ssl=false"

# 启动 Flume Agent
nohup ${FLUME_HOME}/bin/flume-ng agent \
    --name ${AGENT_NAME} \
    --conf-file ${CONF_FILE} \
    --classpath lib/*:${FLUME_HOME}/lib/* \
    -Dflume.root.logger=INFO,LOGFILE \
    -Dflume.log.dir=${LOG_DIR} \
    -Dflume.log.file=flume-agent.log \
    > ${LOG_DIR}/nohup.out 2>&1 &

# 保存 PID
echo $! > ${PID_FILE}

echo "Flume Agent 已启动, PID: $!"
echo "日志目录: ${LOG_DIR}"
echo "配置文件: ${CONF_FILE}"
