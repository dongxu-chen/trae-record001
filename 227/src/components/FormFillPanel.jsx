import { useState, useEffect } from 'react';
import { extractFormFields } from '../utils/pdfform';

export function FormFillPanel({ pdfDoc, onClose }) {
  const [formFields, setFormFields] = useState([]);
  const [formData, setFormData] = useState({});
  const [loading, setLoading] = useState(true);
  const [currentPageFields, setCurrentPageFields] = useState([]);
  const [selectedPage, setSelectedPage] = useState(1);

  useEffect(() => {
    if (pdfDoc) {
      loadFormFields();
    }
  }, [pdfDoc]);

  useEffect(() => {
    const pageFields = formFields.filter(f => f.pageNum === selectedPage);
    setCurrentPageFields(pageFields);
  }, [formFields, selectedPage]);

  const loadFormFields = async () => {
    setLoading(true);
    try {
      const fields = await extractFormFields(pdfDoc);
      setFormFields(fields);
      
      const initialData = {};
      fields.forEach(field => {
        initialData[field.name] = field.value;
      });
      setFormData(initialData);
      
      if (fields.length > 0) {
        setSelectedPage(fields[0].pageNum);
      }
    } catch (error) {
      console.error('加载表单字段失败:', error);
    }
    setLoading(false);
  };

  const handleFieldChange = (fieldName, value) => {
    setFormData(prev => ({
      ...prev,
      [fieldName]: value
    }));
  };

  const handleCheckboxChange = (fieldName, checked) => {
    setFormData(prev => ({
      ...prev,
      [fieldName]: checked ? 'Yes' : 'Off'
    }));
  };

  const getFieldTypeLabel = (type) => {
    const types = {
      'Tx': '文本框',
      'Btn': '按钮/复选框',
      'Ch': '下拉选择',
      'Sig': '签名'
    };
    return types[type] || type;
  };

  const pagesWithFields = [...new Set(formFields.map(f => f.pageNum))].sort((a, b) => a - b);

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
        width: '80%',
        maxWidth: '700px',
        maxHeight: '80vh',
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
          <h3 style={{ margin: 0 }}>📝 PDF表单填充</h3>
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

        <div style={{ padding: '24px', overflowY: 'auto', flex: 1 }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '40px' }}>
              <p>正在识别表单字段...</p>
            </div>
          ) : formFields.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px', color: '#666' }}>
              <p style={{ fontSize: '48px', margin: 0 }}>📋</p>
              <p>未检测到可填写的表单字段</p>
              <p style={{ fontSize: '14px' }}>此PDF可能不包含交互式表单</p>
            </div>
          ) : (
            <>
              <div style={{ marginBottom: '16px' }}>
                <p style={{ margin: '0 0 8px 0', fontSize: '14px', color: '#666' }}>
                  共检测到 <strong>{formFields.length}</strong> 个表单字段
                </p>
                {pagesWithFields.length > 1 && (
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    <span style={{ fontSize: '14px', color: '#666' }}>选择页面:</span>
                    {pagesWithFields.map(page => (
                      <button
                        key={page}
                        onClick={() => setSelectedPage(page)}
                        style={{
                          padding: '4px 12px',
                          border: `1px solid ${selectedPage === page ? '#3498db' : '#ddd'}`,
                          background: selectedPage === page ? '#3498db' : 'white',
                          color: selectedPage === page ? 'white' : '#333',
                          borderRadius: '4px',
                          cursor: 'pointer'
                        }}
                      >
                        第{page}页
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <div style={{ display: 'grid', gap: '16px' }}>
                {currentPageFields.map((field, index) => (
                  <div key={index} style={{
                    padding: '12px',
                    border: '1px solid #e0e0e0',
                    borderRadius: '6px'
                  }}>
                    <div style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      marginBottom: '8px'
                    }}>
                      <label style={{ fontWeight: 500 }}>
                        {field.name}
                        {field.required && <span style={{ color: 'red' }}> *</span>}
                      </label>
                      <span style={{
                        fontSize: '12px',
                        color: '#999',
                        background: '#f5f5f5',
                        padding: '2px 8px',
                        borderRadius: '4px'
                      }}>
                        {getFieldTypeLabel(field.type)}
                      </span>
                    </div>

                    {field.type === 'Tx' && (
                      field.multiline ? (
                        <textarea
                          value={formData[field.name] || ''}
                          onChange={(e) => handleFieldChange(field.name, e.target.value)}
                          readOnly={field.readOnly}
                          placeholder={field.defaultValue || ''}
                          style={{
                            width: '100%',
                            minHeight: '80px',
                            padding: '8px 12px',
                            border: '1px solid #ddd',
                            borderRadius: '4px',
                            resize: 'vertical',
                            fontFamily: 'inherit'
                          }}
                        />
                      ) : (
                        <input
                          type={field.password ? 'password' : 'text'}
                          value={formData[field.name] || ''}
                          onChange={(e) => handleFieldChange(field.name, e.target.value)}
                          readOnly={field.readOnly}
                          placeholder={field.defaultValue || ''}
                          style={{
                            width: '100%',
                            padding: '8px 12px',
                            border: '1px solid #ddd',
                            borderRadius: '4px'
                          }}
                        />
                      )
                    )}

                    {field.type === 'Btn' && (
                      <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                        <input
                          type="checkbox"
                          checked={formData[field.name] === 'Yes'}
                          onChange={(e) => handleCheckboxChange(field.name, e.target.checked)}
                          disabled={field.readOnly}
                          style={{ width: '18px', height: '18px', marginRight: '8px' }}
                        />
                        <span>勾选此选项</span>
                      </label>
                    )}

                    {field.type === 'Ch' && field.options && field.options.length > 0 && (
                      <select
                        value={formData[field.name] || ''}
                        onChange={(e) => handleFieldChange(field.name, e.target.value)}
                        disabled={field.readOnly}
                        style={{
                          width: '100%',
                          padding: '8px 12px',
                          border: '1px solid #ddd',
                          borderRadius: '4px'
                        }}
                      >
                        <option value="">请选择...</option>
                        {field.options.map((opt, i) => (
                          <option key={i} value={opt}>{opt}</option>
                        ))}
                      </select>
                    )}
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

        <div style={{
          padding: '16px 24px',
          borderTop: '1px solid #e0e0e0',
          display: 'flex',
          justifyContent: 'flex-end',
          gap: '12px'
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
          {formFields.length > 0 && (
            <button
              onClick={() => {
                alert('表单数据已保存！\n\n' + JSON.stringify(formData, null, 2));
              }}
              style={{
                padding: '8px 24px',
                border: 'none',
                background: '#27ae60',
                color: 'white',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              保存表单
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
