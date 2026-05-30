import { useState, useMemo } from 'react'
import CrossTableEngine from '../utils/crossTableEngine'

function CrossTablePanel({ data, onApplySuggestion }) {
  const [mode, setMode] = useState('fill')
  const [refTableName, setRefTableName] = useState('')
  const [refTableData, setRefTableData] = useState('')
  const [refKeyName, setRefKeyName] = useState('')
  const [refValueNames, setRefValueNames] = useState('')
  const [selectedTable, setSelectedTable] = useState('')
  const [matchColumn, setMatchColumn] = useState('')
  const [fillColumn, setFillColumn] = useState('')
  const [previewResults, setPreviewResults] = useState(null)

  const crossTableEngine = useMemo(() => new CrossTableEngine(), [])
  const availableTables = useMemo(() => crossTableEngine.getAvailableTables(), [crossTableEngine])

  const handleAddTable = () => {
    if (!refTableName.trim() || !refTableData.trim()) return

    const lines = refTableData.trim().split('\n').filter(l => l.trim())
    if (lines.length < 2) return

    const tableData = lines.map(line => line.split(/[,\t]/).map(v => v.trim().replace(/^"|"$/g, '')))
    
    const keyCol = refKeyName.trim() || tableData[0][0]
    const valueCols = refValueNames.trim() 
      ? refValueNames.split(/[,，]/).map(v => v.trim()).filter(v => v)
      : tableData[0].slice(1)

    const result = crossTableEngine.addReferenceTable(refTableName.trim(), tableData, keyCol, valueCols)
    
    if (result) {
      setRefTableName('')
      setRefTableData('')
      setRefKeyName('')
      setRefValueNames('')
    }
  }

  const handlePreviewFill = () => {
    if (!selectedTable || !matchColumn || !fillColumn) return

    const headers = data[0]
    const matchIdx = headers.indexOf(matchColumn)
    if (matchIdx < 0) return

    const sourceColumnData = data.slice(1).map(row => row[matchIdx])
    const results = crossTableEngine.fillFromReference(selectedTable, sourceColumnData, fillColumn)
    
    setPreviewResults(results)
  }

  const handleApplyFill = () => {
    if (!selectedTable || !matchColumn || !fillColumn) return

    onApplySuggestion(
      {
        id: 'cross_table_lookup',
        name: '跨表关联填充',
        description: `从「${selectedTable}」表根据「${matchColumn}」查找「${fillColumn}」`,
        example: `${matchColumn} → ${fillColumn} (来自${selectedTable})`
      },
      {
        refTableName: selectedTable,
        keyColumnName: matchColumn,
        valueColumnName: fillColumn,
        fillEmptyOnly: true
      }
    )
  }

  const handleDeleteTable = (name) => {
    crossTableEngine.removeReferenceTable(name)
    if (selectedTable === name) {
      setSelectedTable('')
    }
  }

  const suggestedMappings = useMemo(() => {
    if (!selectedTable || !data?.[0]) return []
    return crossTableEngine.suggestMapping(data[0], selectedTable)
  }, [selectedTable, data, crossTableEngine])

  return (
    <div>
      <div style={{ display: 'flex', gap: '6px', marginBottom: '12px' }}>
        <button
          className={`btn ${mode === 'fill' ? 'btn-primary' : 'btn-default'}`}
          style={{ padding: '4px 10px', fontSize: '12px' }}
          onClick={() => setMode('fill')}
        >
          关联填充
        </button>
        <button
          className={`btn ${mode === 'add' ? 'btn-primary' : 'btn-default'}`}
          style={{ padding: '4px 10px', fontSize: '12px' }}
          onClick={() => setMode('add')}
        >
          添加参考表
        </button>
        <button
          className={`btn ${mode === 'manage' ? 'btn-primary' : 'btn-default'}`}
          style={{ padding: '4px 10px', fontSize: '12px' }}
          onClick={() => setMode('manage')}
        >
          管理表
        </button>
      </div>

      {mode === 'add' && (
        <div>
          <div className="form-group">
            <label>表名称</label>
            <input
              type="text"
              value={refTableName}
              onChange={(e) => setRefTableName(e.target.value)}
              placeholder="例如: 部门对照表"
            />
          </div>
          <div className="form-group">
            <label>数据 (CSV格式，第一行为表头)</label>
            <textarea
              value={refTableData}
              onChange={(e) => setRefTableData(e.target.value)}
              placeholder={'部门代码,部门名称,负责人\nD001,技术部,张三\nD002,产品部,李四\nD003,市场部,王五'}
              style={{ width: '100%', minHeight: '100px', padding: '8px 12px', fontFamily: 'monospace', fontSize: '13px' }}
            />
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <div className="form-group" style={{ flex: 1 }}>
              <label>键列名</label>
              <input
                type="text"
                value={refKeyName}
                onChange={(e) => setRefKeyName(e.target.value)}
                placeholder="默认第一列"
              />
            </div>
            <div className="form-group" style={{ flex: 1 }}>
              <label>取值列名</label>
              <input
                type="text"
                value={refValueNames}
                onChange={(e) => setRefValueNames(e.target.value)}
                placeholder="默认其余列"
              />
            </div>
          </div>
          <button
            className="btn btn-primary"
            style={{ width: '100%', justifyContent: 'center' }}
            onClick={handleAddTable}
          >
            添加参考表
          </button>
        </div>
      )}

      {mode === 'fill' && (
        <div>
          {availableTables.length === 0 ? (
            <div className="empty-state">
              <div style={{ fontSize: '28px', marginBottom: '8px' }}>🔗</div>
              <div>暂无参考表</div>
              <div style={{ fontSize: '12px', marginTop: '4px' }}>
                先添加参考表才能进行跨表关联
              </div>
            </div>
          ) : (
            <>
              <div className="form-group">
                <label>选择参考表</label>
                <select
                  value={selectedTable}
                  onChange={(e) => setSelectedTable(e.target.value)}
                >
                  <option value="">-- 选择参考表 --</option>
                  {availableTables.map(t => (
                    <option key={t.name} value={t.name}>
                      {t.name} (键: {t.keyColumn}, {t.rowCount}行)
                    </option>
                  ))}
                </select>
              </div>

              {selectedTable && (
                <>
                  {suggestedMappings.length > 0 && (
                    <div style={{
                      padding: '8px 10px',
                      background: '#f0fdf4',
                      borderRadius: '6px',
                      marginBottom: '12px',
                      fontSize: '12px',
                      color: '#166534'
                    }}>
                      <div style={{ fontWeight: 600, marginBottom: '4px' }}>🔍 自动匹配建议</div>
                      {suggestedMappings.slice(0, 3).map((m, i) => (
                        <div key={i}>
                          {m.currentColumn} ↔ {m.refColumn} {m.isKey ? '(键)' : ''} ({Math.round(m.confidence * 100)}%)
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="form-group">
                    <label>匹配列（当前表中的列）</label>
                    <select
                      value={matchColumn}
                      onChange={(e) => setMatchColumn(e.target.value)}
                    >
                      <option value="">-- 选择匹配列 --</option>
                      {data[0]?.map((h, i) => (
                        <option key={i} value={h}>{h}</option>
                      ))}
                    </select>
                  </div>

                  <div className="form-group">
                    <label>取值列（参考表中的列）</label>
                    <select
                      value={fillColumn}
                      onChange={(e) => setFillColumn(e.target.value)}
                    >
                      <option value="">-- 选择取值列 --</option>
                      {availableTables
                        .find(t => t.name === selectedTable)
                        ?.valueColumns.map((vc, i) => (
                          <option key={i} value={vc}>{vc}</option>
                        ))}
                    </select>
                  </div>

                  {matchColumn && fillColumn && (
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button
                        className="btn btn-warning"
                        style={{ flex: 1, justifyContent: 'center', fontSize: '13px' }}
                        onClick={handlePreviewFill}
                      >
                        预览
                      </button>
                      <button
                        className="btn btn-success"
                        style={{ flex: 1, justifyContent: 'center', fontSize: '13px' }}
                        onClick={handleApplyFill}
                      >
                        应用
                      </button>
                    </div>
                  )}

                  {previewResults && (
                    <div style={{
                      marginTop: '12px',
                      padding: '8px 10px',
                      background: '#fef3c7',
                      borderRadius: '6px',
                      fontSize: '12px'
                    }}>
                      <div style={{ fontWeight: 600, color: '#92400e', marginBottom: '4px' }}>预览结果</div>
                      <div style={{ color: '#78350f' }}>
                        匹配成功: {previewResults.filter(v => v !== undefined && v !== '').length} / {previewResults.length}
                      </div>
                      <div style={{ marginTop: '4px', color: '#6b7280', fontFamily: 'monospace', fontSize: '11px' }}>
                        {previewResults.slice(0, 5).map((v, i) => (
                          <div key={i}>行{i + 2}: {v ?? '(无匹配)'}</div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}
            </>
          )}
        </div>
      )}

      {mode === 'manage' && (
        <div>
          {availableTables.length === 0 ? (
            <div className="empty-state">
              <div style={{ fontSize: '28px', marginBottom: '8px' }}>📋</div>
              <div>暂无参考表</div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {availableTables.map(t => (
                <div
                  key={t.name}
                  style={{
                    padding: '10px 12px',
                    border: '1px solid #e5e7eb',
                    borderRadius: '8px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 500, fontSize: '14px', color: '#374151' }}>
                      {t.name}
                    </div>
                    <div style={{ fontSize: '12px', color: '#6b7280' }}>
                      键: {t.keyColumn} · 取值: {t.valueColumns.join(', ')} · {t.rowCount}行
                    </div>
                  </div>
                  <button
                    className="btn btn-default"
                    style={{ padding: '4px 8px', fontSize: '12px', color: '#dc2626' }}
                    onClick={() => handleDeleteTable(t.name)}
                  >
                    删除
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default CrossTablePanel
