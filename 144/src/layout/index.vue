<template>
  <el-container class="layout-container">
    <el-aside width="240px" class="sidebar">
      <div class="logo">
        <el-icon size="32"><Odometer /></el-icon>
        <span>Tekton Builder</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        class="nav-menu"
        router
      >
        <el-menu-item index="/pipeline">
          <el-icon><Operation /></el-icon>
          <span>流水线编辑器</span>
        </el-menu-item>
        <el-menu-item index="/templates">
          <el-icon><Collection /></el-icon>
          <span>模板市场</span>
        </el-menu-item>
        <el-menu-item index="/pipelines">
          <el-icon><List /></el-icon>
          <span>流水线运行</span>
        </el-menu-item>
        <el-menu-item index="/tasks">
          <el-icon><Box /></el-icon>
          <span>任务库</span>
        </el-menu-item>
        <el-menu-item index="/triggers">
          <el-icon><Bell /></el-icon>
          <span>GitOps触发器</span>
        </el-menu-item>
        <el-menu-item index="/analytics">
          <el-icon><DataLine /></el-icon>
          <span>趋势分析</span>
        </el-menu-item>
        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon>
          <span>系统设置</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container class="main-container">
      <el-header class="header">
        <div class="header-title">{{ currentPageTitle }}</div>
        <div class="header-actions">
          <el-tag type="info" size="small">
            <el-icon size="12"><Cloud /></el-icon>
            K8s: Connected
          </el-tag>
          <el-tag type="success" size="small">
            <el-icon size="12"><Connection /></el-icon>
            Tekton: Ready
          </el-tag>
        </div>
      </el-header>
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  Odometer, Operation, Collection, List, Box, Bell, DataLine, Setting,
  Cloud, Connection
} from '@element-plus/icons-vue'

const route = useRoute()
const activeMenu = computed(() => route.path)
const currentPageTitle = computed(() => route.meta.title || 'Tekton Builder')
</script>

<style scoped>
.layout-container {
  height: 100vh;
}

.sidebar {
  background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
  display: flex;
  flex-direction: column;
  border-right: 1px solid #334155;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px;
  color: white;
  font-size: 18px;
  font-weight: bold;
  border-bottom: 1px solid #334155;
}

.logo .el-icon {
  color: #3b82f6;
}

.nav-menu {
  flex: 1;
  border-right: none;
  background: transparent;
}

.nav-menu :deep(.el-menu-item) {
  color: rgba(255, 255, 255, 0.7);
  margin: 4px 12px;
  border-radius: 8px;
  height: 48px;
  line-height: 48px;
}

.nav-menu :deep(.el-menu-item:hover) {
  color: white;
  background: rgba(59, 130, 246, 0.2);
}

.nav-menu :deep(.el-menu-item.is-active) {
  color: white;
  background: #3b82f6;
}

.main-container {
  display: flex;
  flex-direction: column;
  background: #f8fafc;
}

.header {
  background: white;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  height: 60px;
}

.header-title {
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.main-content {
  background: #f8fafc;
  padding: 24px;
  overflow: auto;
}
</style>
