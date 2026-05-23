import { useState } from 'react';
import {
  splitPDFPages,
  parsePageRange,
  validateSplitRanges,
  downloadAsJSON
} from '../utils/pdfMergeSplit';

export function MergeSplitPanel({ pdfDoc, numPages, onClose }) {
  const [activeTab, setActiveTab] = useState('merge');
  const [mergeFiles, setMergeFiles] = useState([]);
  const [splitRanges, setSplitRanges] = useState([{ start: 1, end: Math.ceil(numPages / 2), name: '第一部分' }]);
  const [splitResults, setSplitResults] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleMergeFilesChange = (e) => {
    const files = Array.from(e.target.files);
    const validFiles = files.filter(f => f.type === 'application/pdf');
    
    if (validFiles.length < files.length) {
      alert('部分文件不是有效的PDF文件，已自动过滤');
    }
    
    setMergeFiles(prev => [...prev, ...validFiles].slice(0, 10));
  };

  const removeMergeFile = (index) => {
    setMergeFiles(prev => prev.filter((_, i) => i !== index));
  };

  const moveMergeFile = (fromIndex, direction) => {
    const toIndex = fromIndex + direction;
    if (toIndex < 0 || toIndex >= mergeFiles.length) return;
    
    setMergeFiles(prev => {
      const newFiles = [...prev];
      [newFiles[fromIndex], newFiles[toIndex]] = [newFiles[toIndex], newFiles[fromIndex]];
      return newFiles;
    });
  };

  const handleMerge = async () => {
    if (mergeFiles.length < 2) {
      alert('请至少选择2个PDF文件进行合并');
      return;
    }

    setLoading(true);
    try {
      const mergedData = {
        type: 'merged',
        files: mergeFiles.map(f => ({ name: f.name, size: f.size })),
        totalFiles: mergeFiles.length,
        createdAt: new Date().toISOString()
      };
      
      downloadAsJSON(mergedData, `merged_${Date.now()}.json`);
      alert('合并信息已导出！\n\n注：完整的PDF合并功能需要服务端支持或pdf-lib库');
    } catch (error) {
      alert('合并失败: ' + error.message);
    }
    setLoading(false);
  };

  const addSplitRange = () => {
    const lastRange = splitRanges[splitRanges.length - 1];
    const nextStart = lastRange ? lastRange.end + 1 : 1;
    
    if (nextStart > numPages) {
      alert('已覆盖所有页面');
      return;
    }
    
    setSplitRanges(prev => [...prev, {
      start: nextStart,
      end: Math.min(nextStart + 4, numPages),
      name: `部分_${prev.length + 1}`
    }]);
  };

  const removeSplitRange = (index) => {
    if (splitRanges.length <= 1) return;
    setSplitRanges(prev => prev.filter((_, i) => i !== index));
  };

  const updateSplitRange = (index, field, value) => {
    setSplitRanges(prev => prev.map((range, i) => 
      i === index ? { ...range, [field]: parseInt(value) || 1 } : range
    ));
  };

  const updateSplitName = (index, value) => {
    setSplitRanges(prev => prev.map((range, i) => 
      i === index ? { ...range, name: value } : range
    ));
  };

  const handleQuickSplit = (parts) => {
    const pagesPerPart = Math.ceil(numPages / parts);
    const ranges = [];
    
    for (let i = 0; i < parts; i++) {
      const start = i * pagesPerPart + 1;
      const end = Math.min((i + 1) * pagesPerPart, numPages);
      if (start <= numPages) {
        ranges.push({ start, end, name: `第${i + 1}部分` });
      }
    }
    
    setSplitRanges(ranges);
  };

  const handleSplit = () => {
    const errors = validateSplitRanges(splitRanges, numPages);
    if (errors.length > 0) {
      alert('拆分范围有误:\n' + errors.join('\n'));
      return;
    }

    setLoading(true);
    try {
      const mockPages = Array.from({ length: numPages }, (_, i) => ({
        pageNum: i + 1,
        data: `page_${i + 1}`
      }));
      
      const results = splitPDFPages(mockPages, splitRanges);
      setSplitResults(results);
    } catch (error) {
      alert('拆分失败: ' + error.message);
    }
    setLoading(false);
  };

  const downloadSplitResult = (result) => {
    downloadAsJSON(result, `${result.name}.json`);
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(0,0,0,0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000
    }}>
      <div style={{
        background: 'white',
        borderRadius: '8px',
        width: '90%',
        maxWidth: '700px',
        maxHeight: '90vh',
        display: 'flex',
        flexDirection: 'column'
      }}>
        <div style={{
          padding: '16px 24px',
          borderBottom: '1px solid #e0e0e0',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <h3 style={{ margin: 0 }}>📦 PDF合并/拆分</h3>
          <button 
            onClick={onClose}
            style={{
              border: 'none',
              background: 'none',
              fontSize: '20px',
              cursor: 'pointer',
              color: '#666'
            }}
          >
            ✕
          </button>
        </div>

        <div style={{
          display: 'flex',
          borderBottom: '1px solid #e0e0e0'
        }}>
          <button
            onClick={() => setActiveTab('merge')}
            style={{
              flex: 1,
              padding: '12px',
              border: 'none',
              background: activeTab === 'merge' ? '#f0f8ff' : 'white',
              borderBottom: `2px solid ${activeTab === 'merge' ? '#3498db' : 'transparent'}`,
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: activeTab === 'merge' ? 600 : 400
            }}
          >
            🔗 合并PDF
          </button>
          <button
            onClick={() => setActiveTab('split')}
            style={{
              flex: 1,
              padding: '12px',
              border: 'none',
              background: activeTab === 'split' ? '#f0f8ff' : 'white',
              borderBottom: `2px solid ${activeTab === 'split' ? '#3498db' : 'transparent'}`,
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: activeTab === 'split' ? 600 : 400
            }}
          >
            ✂️ 拆分PDF
          </button>
        </div>

        <div style={{ padding: '24px', overflowY: 'auto', flex: 1 }}>
          {activeTab === 'merge' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{
                padding: '16px',
                border: '2px dashed #ddd',
                borderRadius: '6px',
                textAlign: 'center'
              }}>
                <input
                  type="file"
                  accept=".pdf"
                  multiple
                  onChange={handleMergeFilesChange}
                  style={{ marginBottom: '8px' }}
                />
                <p style={{ margin: 0, fontSize: '13px', color: '#666' }}>
                  选择多个PDF文件，按顺序合并
                </p>
              </div>

              {mergeFiles.length > 0 && (
                <div>
                  <p style={{ margin: '0 0 8px 0', fontWeight: 500 }}>
                    待合并文件 ({mergeFiles.length}个):
                  </p>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {mergeFiles.map((file, index) => (
                      <div
                        key={index}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          padding: '10px 12px',
                          background: '#f5f5f5',
                          borderRadius: '4px'
                        }}
                      >
                        <span style={{
                          width: '24px',
                          height: '24px',
                          background: '#3498db',
                          color: 'white',
                          borderRadius: '50%',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontSize: '12px',
                          marginRight: '12px'
                        }}>
                          {index + 1}
                        </span>
                        <div style={{ flex: 1, overflow: 'hidden' }}>
                          <div style={{ 
                            fontWeight: 500, 
                            whiteSpace: 'nowrap', 
                            overflow: 'hidden', 
                            textOverflow: 'ellipsis' 
                          }}>
                            {file.name}
                          </div>
                          <div style={{ fontSize: '12px', color: '#666' }}>
                            {(file.size / 1024).toFixed(1)} KB
                          </div>
                        </div>
                        <div style={{ display: 'flex', gap: '4px' }}>
                          <button
                            onClick={() => moveMergeFile(index, -1)}
                            disabled={index === 0}
                            style={{
                              padding: '4px 8px',
                              border: '1px solid #ddd',
                              background: index === 0 ? '#f0f0f0' : 'white',
                              cursor: index === 0 ? 'not-allowed' : 'pointer',
                              borderRadius: '4px'
                            }}
                          >
                            ↑
                          </button>
                          <button
                            onClick={() => moveMergeFile(index, 1)}
                            disabled={index === mergeFiles.length - 1}
                            style={{
                              padding: '4px 8px',
                              border: '1px solid #ddd',
                              background: index === mergeFiles.length - 1 ? '#f0f0f0' : 'white',
                              cursor: index === mergeFiles.length - 1 ? 'not-allowed' : 'pointer',
                              borderRadius: '4px'
                            }}
                          >
                            ↓
                          </button>
                          <button
                            onClick={() => removeMergeFile(index)}
                            style={{
                              padding: '4px 8px',
                              border: '1px solid #e57373',
                              background: 'white',
                              color: '#e57373',
                              cursor: 'pointer',
                              borderRadius: '4px'
                            }}
                          >
                            ✕
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <button
                onClick={handleMerge}
                disabled={loading || mergeFiles.length < 2}
                style={{
                  padding: '12px',
                  border: 'none',
                  background: '#27ae60',
                  color: 'white',
                  borderRadius: '4px',
                  fontSize: '16px',
                  cursor: (loading || mergeFiles.length < 2) ? 'not-allowed' : 'pointer',
                  opacity: (loading || mergeFiles.length < 2) ? 0.6 : 1
                }}
              >
                {loading ? '合并中...' : '🔗 开始合并'}
              </button>

              <div style={{
                padding: '12px',
                background: '#fff8e1',
                borderRadius: '4px',
                fontSize: '12px',
                color: '#f57f17'
              }}>
                💡 提示：完整的PDF合并功能需要服务端支持或使用pdf-lib等专业库。
                当前导出合并元数据供演示使用。
              </div>
            </div>
          )}

          {activeTab === 'split' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{
                padding: '12px',
                background: '#e3f2fd',
                borderRadius: '4px',
                fontSize: '14px'
              }}>
                <strong>当前文档:</strong> 共 {numPages} 页
              </div>

              <div>
                <p style={{ margin: '0 0 8px 0', fontSize: '14px' }}>快速拆分:</p>
                <div style={{ display: 'flex', gap: '8px' }}>
                  {[2, 3, 4, 5].map(n => (
                    <button
                      key={n}
                      onClick={() => handleQuickSplit(n)}
                      style={{
                        padding: '6px 16px',
                        border: '1px solid #3498db',
                        background: 'white',
                        color: '#3498db',
                        borderRadius: '4px',
                        cursor: 'pointer'
                      }}
                    >
                      {n}等分
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <p style={{ margin: '0 0 8px 0', fontSize: '14px', fontWeight: 500 }}>
                    自定义拆分范围:
                  </p>
                  <button
                    onClick={addSplitRange}
                    style={{
                      padding: '4px 12px',
                      border: '1px solid #27ae60',
                      background: 'white',
                      color: '#27ae60',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      fontSize: '12px'
                    }}
                  >
                    + 添加范围
                  </button>
                </div>
                
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {splitRanges.map((range, index) => (
                    <div
                      key={index}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        padding: '10px',
                        background: '#f5f5f5',
                        borderRadius: '4px'
                      }}
                    >
                      <input
                        type="text"
                        value={range.name}
                        onChange={(e) => updateSplitName(index, e.target.value)}
                        placeholder="名称"
                        style={{
                          flex: 1,
                          padding: '6px 8px',
                          border: '1px solid #ddd',
                          borderRadius: '4px',
                          minWidth: '80px'
                        }}
                      />
                      <span style={{ fontSize: '14px', color: '#666' }}>页码:</span>
                      <input
                        type="number"
                        min="1"
                        max={numPages}
                        value={range.start}
                        onChange={(e) => updateSplitRange(index, 'start', e.target.value)}
                        style={{
                          width: '60px',
                          padding: '6px 8px',
                          border: '1px solid #ddd',
                          borderRadius: '4px'
                        }}
                      />
                      <span style={{ color: '#999' }}>-</span>
                      <input
                        type="number"
                        min="1"
                        max={numPages}
                        value={range.end}
                        onChange={(e) => updateSplitRange(index, 'end', e.target.value)}
                        style={{
                          width: '60px',
                          padding: '6px 8px',
                          border: '1px solid #ddd',
                          borderRadius: '4px'
                        }}
                      />
                      <span style={{ fontSize: '12px', color: '#666' }}>
                        ({range.end - range.start + 1}页)
                      </span>
                      {splitRanges.length > 1 && (
                        <button
                          onClick={() => removeSplitRange(index)}
                          style={{
                            padding: '4px 8px',
                            border: '1px solid #e57373',
                            background: 'white',
                            color: '#e57373',
                            cursor: 'pointer',
                            borderRadius: '4px'
                          }}
                        >
                          ✕
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              <button
                onClick={handleSplit}
                disabled={loading || splitRanges.length === 0}
                style={{
                  padding: '12px',
                  border: 'none',
                  background: '#e67e22',
                  color: 'white',
                  borderRadius: '4px',
                  fontSize: '16px',
                  cursor: (loading || splitRanges.length === 0) ? 'not-allowed' : 'pointer',
                  opacity: (loading || splitRanges.length === 0) ? 0.6 : 1
                }}
              >
                {loading ? '拆分中...' : '✂️ 开始拆分'}
              </button>

              {splitResults.length > 0 && (
                <div>
                  <p style={{ margin: '0 0 8px 0', fontWeight: 600, color: '#27ae60' }}>
                    ✅ 拆分完成！
                  </p>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {splitResults.map((result, index) => (
                      <div
                        key={index}
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          padding: '10px 12px',
                          background: '#e8f5e9',
                          borderRadius: '4px'
                        }}
                      >
                        <div>
                          <strong>{result.name}</strong>
                          <span style={{ 
                            fontSize: '12px', 
                            color: '#666', 
                            marginLeft: '12px' 
                          }}>
                            {result.pageRange} ({result.pages.length}页)
                          </span>
                        </div>
                        <button
                          onClick={() => downloadSplitResult(result)}
                          style={{
                            padding: '6px 16px',
                            border: '1px solid #27ae60',
                            background: 'white',
                            color: '#27ae60',
                            borderRadius: '4px',
                            cursor: 'pointer'
                          }}
                        >
                          📥 导出
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        <div style={{
          padding: '16px 24px',
          borderTop: '1px solid #e0e0e0',
          display: 'flex',
          justifyContent: 'flex-end'
        }}>
          <button
            onClick={onClose}
            style={{
              padding: '8px 24px',
              border: '1px solid #ddd',
              background: 'white',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            关闭
          </button>
        </div>
      </div>
    </div>
  );
}
