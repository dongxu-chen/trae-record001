import React, { useState, useEffect } from 'react';
import { getTestCases, createTestCase, updateTestCase, deleteTestCase } from '../utils/api';

const TestCaseManager = ({ onLoadTestCase, currentPattern, currentTestText }) => {
  const [testCases, setTestCases] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [editingCase, setEditingCase] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    pattern: '',
    testText: ''
  });

  useEffect(() => {
    loadTestCases();
  }, []);

  const loadTestCases = async () => {
    try {
      const data = await getTestCases();
      setTestCases(data);
    } catch (error) {
      console.error('加载测试用例失败:', error);
    }
  };

  const handleCreate = () => {
    setEditingCase(null);
    setFormData({
      name: '',
      pattern: currentPattern,
      testText: currentTestText
    });
    setShowModal(true);
  };

  const handleEdit = (testCase) => {
    setEditingCase(testCase);
    setFormData({
      name: testCase.name,
      pattern: testCase.pattern,
      testText: testCase.testText
    });
    setShowModal(true);
  };

  const handleSave = async () => {
    if (!formData.name.trim()) {
      alert('请输入测试用例名称');
      return;
    }

    try {
      if (editingCase) {
        await updateTestCase(editingCase.id, formData);
      } else {
        await createTestCase(formData);
      }
      await loadTestCases();
      setShowModal(false);
    } catch (error) {
      console.error('保存失败:', error);
      alert('保存失败，请重试');
    }
  };

  const handleDelete = async (id, e) => {
    e.stopPropagation();
    if (!confirm('确定要删除这个测试用例吗？')) return;

    try {
      await deleteTestCase(id);
      await loadTestCases();
    } catch (error) {
      console.error('删除失败:', error);
      alert('删除失败，请重试');
    }
  };

  const formatDate = (timestamp) => {
    return new Date(timestamp).toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div>
      <div className="panel-header">
        <span>测试用例管理</span>
        <button className="btn btn-sm btn-primary" onClick={handleCreate}>
          + 新建
        </button>
      </div>

      <div className="panel-body">
        {testCases.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">📋</div>
            <p>暂无测试用例</p>
            <p style={{ fontSize: '12px', marginTop: '8px' }}>点击上方按钮创建第一个测试用例</p>
          </div>
        ) : (
          <div className="test-case-list">
            {testCases.map((testCase) => (
              <div
                key={testCase.id}
                className="test-case-item"
                onClick={() => onLoadTestCase(testCase)}
              >
                <div className="test-case-name">{testCase.name}</div>
                <div className="test-case-pattern">{testCase.pattern}</div>
                <div className="test-case-date">
                  创建于 {formatDate(testCase.createdAt)}
                </div>
                <div className="test-case-actions">
                  <button
                    className="btn btn-sm btn-secondary"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleEdit(testCase);
                    }}
                  >
                    编辑
                  </button>
                  <button
                    className="btn btn-sm btn-danger"
                    onClick={(e) => handleDelete(testCase.id, e)}
                  >
                    删除
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              {editingCase ? '编辑测试用例' : '新建测试用例'}
            </div>

            <div className="form-group">
              <label className="form-label">名称</label>
              <input
                type="text"
                className="form-input"
                placeholder="请输入测试用例名称"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </div>

            <div className="form-group">
              <label className="form-label">正则表达式</label>
              <input
                type="text"
                className="form-input"
                placeholder="请输入正则表达式"
                value={formData.pattern}
                onChange={(e) => setFormData({ ...formData, pattern: e.target.value })}
              />
            </div>

            <div className="form-group">
              <label className="form-label">测试文本</label>
              <textarea
                className="form-input form-textarea"
                placeholder="请输入测试文本"
                value={formData.testText}
                onChange={(e) => setFormData({ ...formData, testText: e.target.value })}
              />
            </div>

            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setShowModal(false)}>
                取消
              </button>
              <button className="btn btn-primary" onClick={handleSave}>
                保存
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TestCaseManager;
