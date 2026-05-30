# Kubernetes Network Policy Recommender

Kubernetes网络策略推荐工具，基于Cilium流量分析，推荐最小权限网络策略。

## 功能特性

- 流量收集与分析 - 基于Cilium Hubble收集Pod间通信流量
- 拓扑可视化 - Neo4j图数据库存储通信拓扑
- 策略生成 - 自动推荐最小权限网络策略
- 策略仿真 - 模拟策略应用效果
- 冲突检测 - 检测网络策略冲突

## 技术栈

- **后端**: Go + Gin
- **流量监控**: Cilium Hubble
- **图数据库**: Neo4j
- **前端**: React + TypeScript
- **可视化**: D3.js / Cytoscape.js

## 快速开始

### 后端启动

```bash
# 启动Neo4j
docker-compose up -d neo4j

# 运行后端
cd backend
go run main.go

# 运行前端
cd frontend
npm install
npm start
```
