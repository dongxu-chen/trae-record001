#!/bin/bash
# ============================================
# Flume 停止脚本
# ============================================

PID_FILE=flume-agent.pid

if [ -f ${PID_FILE} ]; then
    PID=$(cat ${PID_FILE})
    if ps -p ${PID} > /dev/null; then
        echo "正在停止 Flume Agent (PID: ${PID})..."
        kill ${PID}
        
        # 等待进程结束
        for i in {1..30}; do
            if ps -p ${PID} > /dev/null; then
                sleep 1
            else
                echo "Flume Agent 已停止"
                rm -f ${PID_FILE}
                exit 0
            fi
        done
        
        # 强制杀死进程
        echo "强制停止 Flume Agent..."
        kill -9 ${PID}
        rm -f ${PID_FILE}
    else
        echo "进程不存在, 清理 PID 文件"
        rm -f ${PID_FILE}
    fi
else
    echo "PID 文件不存在"
fi
