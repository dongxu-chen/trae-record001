import React, { useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import {
  applyTemplate,
  refreshData,
  saveLayout,
  loadLayout,
  clearLayout,
  clearFilters,
} from '../store/dashboardSlice'
import { exportToPDF, exportToPDFWithHeader } from '../utils/exportPDF'
import { eventBus, EVENTS } from '../utils/eventBus'

export default function Toolbar({ onOpenMarket, onOpenAlerts }) {
  const dispatch = useDispatch()
  const templates = useSelector((state) => state.dashboard.templates)
  const lastUpdated = useSelector((state) => state.dashboard.lastUpdated)
  const isRefreshing = useSelector((state) => state.dashboard.isRefreshing)
  const filters = useSelector((state) => state.dashboard.filters)
  const alerts = useSelector((state) => state.dashboard.alerts)
  const [showTemplates, setShowTemplates] = useState(false)
  const [showExportMenu, setShowExportMenu] = useState(false)

  const activeAlerts = alerts.filter(a => a.enabled && a.isActive)

  const handleRefresh = () => {
    dispatch(refreshData())
  }

  const handleSave = () => {
    dispatch(saveLayout())
    alert('布局已保存到本地存储')
  }

  const handleLoad = () => {
    dispatch(loadLayout())
  }

  const handleClear = () => {
    if (confirm('确定要清空所有组件吗？')) {
      dispatch(clearLayout())
    }
  }

  const handleExportPDF = () => {
    setShowExportMenu(!showExportMenu)
  }

  const handleExportSimple = () => {
    exportToPDF()
    setShowExportMenu(false)
  }

  const handleExportWithHeader = () => {
    exportToPDFWithHeader()
    setShowExportMenu(false)
  }

  const handleApplyTemplate = (templateId) => {
    dispatch(applyTemplate(templateId))
    setShowTemplates(false)
  }

  const activeFilters = Object.entries(filters).filter(([_, v]) => v && v !== '全部')

  return (
    <div className="toolbar">
      <div className="toolbar-left">
        <h1 className="app-title">📊 动态仪表板构建器</h1>
        {lastUpdated && (
          <span className="last-updated">
            最后更新: {new Date(lastUpdated).toLocaleString('zh-CN')}
          </span>
        )}
      </div>

      <div className="toolbar-right">
        {activeFilters.length > 0 && (
          <button
            className="toolbar-btn filter-indicator"
            onClick={() => {
              dispatch(clearFilters())
              eventBus.emit(EVENTS.FILTER_CLEARED)
            }}
          >
            🎯 清除筛选 ({activeFilters.length})
          </button>
        )}

        <div className="template-dropdown">
          <button
            className="toolbar-btn template-btn"
            onClick={() => setShowTemplates(!showTemplates)}
          >
            📋 使用模板
          </button>
          {showTemplates && (
            <div className="template-menu">
              {templates.map((template) => (
                <div
                  key={template.id}
                  className="template-item"
                  onClick={() => handleApplyTemplate(template.id)}
                >
                  <div className="template-name">{template.name}</div>
                  <div className="template-desc">{template.description}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        <button className="toolbar-btn market-btn" onClick={onOpenMarket}>
          🏪 组件市场
        </button>

        <button
          className={`toolbar-btn alert-btn ${activeAlerts.length > 0 ? 'has-alerts' : ''}`}
          onClick={onOpenAlerts}
        >
          🔔 预警中心
          {activeAlerts.length > 0 && (
            <span className="alert-count">{activeAlerts.length}</span>
          )}
        </button>

        <button
          className={`toolbar-btn refresh-btn ${isRefreshing ? 'refreshing' : ''}`}
          onClick={handleRefresh}
          disabled={isRefreshing}
        >
          {isRefreshing ? '⏳ 刷新中...' : '🔄 一键刷新'}
        </button>

        <button className="toolbar-btn save-btn" onClick={handleSave}>
          💾 保存布局
        </button>

        <button className="toolbar-btn load-btn" onClick={handleLoad}>
          📂 加载布局
        </button>

        <div className="export-dropdown">
          <button className="toolbar-btn export-btn" onClick={handleExportPDF}>
            📄 导出PDF ▾
          </button>
          {showExportMenu && (
            <div className="export-menu">
              <div className="export-item" onClick={handleExportSimple}>
                <span className="export-icon">📄</span>
                <div>
                  <div className="export-name">标准导出</div>
                  <div className="export-desc">适合短页面，单页输出</div>
                </div>
              </div>
              <div className="export-item" onClick={handleExportWithHeader}>
                <span className="export-icon">📑</span>
                <div>
                  <div className="export-name">报告格式</div>
                  <div className="export-desc">带页眉页脚，长页自动分页</div>
                </div>
              </div>
            </div>
          )}
        </div>

        <button className="toolbar-btn clear-btn" onClick={handleClear}>
          🗑️ 清空
        </button>
      </div>
    </div>
  )
}
