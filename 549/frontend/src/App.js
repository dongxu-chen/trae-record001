import React, { useState, useRef, useEffect } from 'react';
import { Input, Button, Modal, Checkbox, Tag, Select, Upload } from 'antd';
import { SendOutlined, MedicineBoxOutlined, SafetyOutlined, 
         WarningOutlined, FileTextOutlined, SearchOutlined,
         CameraOutlined, InteractionOutlined, PhoneOutlined,
         PlusOutlined, DeleteOutlined, AlertOutlined } from '@ant-design/icons';
import axios from 'axios';

const { TextArea } = Input;

const API_BASE_URL = 'http://localhost:8000';

const quickQuestions = [
  '感冒有什么症状？',
  '高血压吃什么药？',
  '渐冻症有什么症状？',
  '我呼吸困难胸痛怎么办？',
];

const intentMap = {
  'symptom_query': '症状查询',
  'disease_query': '疾病诊断',
  'medicine_query': '用药咨询',
  'treatment_query': '治疗建议',
  'diagnosis_query': '诊断检查',
  'general_query': '通用查询'
};

const DISCLAIMER_TEXT = `【免责声明】

本系统提供的医疗信息仅供参考和教育目的，不能替代专业医生的诊断和治疗建议。

1. 本系统不提供医学诊断，任何健康问题请及时咨询专业医疗人员。
2. 系统回答基于已有知识图谱，可能存在信息滞后或不完整。
3. 罕见病信息仅供参考，罕见病诊断需由专科医生确认。
4. 用药信息仅为一般性介绍，具体用药方案需遵医嘱。
5. 本系统不对信息的准确性、完整性或可靠性做任何保证。
6. 使用本系统产生的任何后果，本系统不承担任何责任。

如果您正在经历紧急医疗状况，请立即拨打120急救电话。`;

function App() {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [disclaimerVisible, setDisclaimerVisible] = useState(false);
  const [disclaimerAgreed, setDisclaimerAgreed] = useState(false);
  const [pendingQuestion, setPendingQuestion] = useState('');
  const [evidenceModalVisible, setEvidenceModalVisible] = useState(false);
  const [currentEvidence, setCurrentEvidence] = useState(null);
  const [activeTab, setActiveTab] = useState('qa');
  const [drugInputs, setDrugInputs] = useState(['', '']);
  const [drugLoading, setDrugLoading] = useState(false);
  const [drugResult, setDrugResult] = useState(null);
  const [skinLoading, setSkinLoading] = useState(false);
  const [skinResult, setSkinResult] = useState(null);
  const [previewImage, setPreviewImage] = useState(null);
  const [emergencyModalVisible, setEmergencyModalVisible] = useState(false);
  const [currentEmergency, setCurrentEmergency] = useState(null);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    const agreed = sessionStorage.getItem('disclaimer_agreed');
    if (agreed === 'true') {
      setDisclaimerAgreed(true);
    } else {
      setDisclaimerVisible(true);
    }
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleDisclaimerAgree = () => {
    setDisclaimerAgreed(true);
    sessionStorage.setItem('disclaimer_agreed', 'true');
    setDisclaimerVisible(false);
    if (pendingQuestion) {
      sendQuestionDirect(pendingQuestion);
      setPendingQuestion('');
    }
  };

  const handleDisclaimerCancel = () => {
    setDisclaimerVisible(false);
    setPendingQuestion('');
  };

  const sendQuestion = (question) => {
    if (!question.trim() || isLoading) return;
    if (!disclaimerAgreed) {
      setPendingQuestion(question);
      setDisclaimerVisible(true);
      return;
    }
    sendQuestionDirect(question);
  };

  const sendQuestionDirect = async (question) => {
    if (!question.trim() || isLoading) return;

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: question
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    const loadingMessage = {
      id: Date.now() + 1,
      type: 'assistant',
      isLoading: true
    };
    setMessages(prev => [...prev, loadingMessage]);

    try {
      const response = await axios.post(`${API_BASE_URL}/api/qa`, {
        question: question
      });

      const data = response.data;
      const assistantMessage = {
        id: Date.now() + 2,
        type: 'assistant',
        content: data.answer,
        intent: data.intent,
        intentConfidence: data.intent_confidence,
        evidence: data.evidence,
        entities: data.entities,
        emergency: data.emergency
      };

      setMessages(prev => prev.filter(m => !m.isLoading));
      setMessages(prev => [...prev, assistantMessage]);

      if (data.emergency && data.emergency.is_emergency) {
        setCurrentEmergency(data.emergency);
        setEmergencyModalVisible(true);
      }
    } catch (error) {
      console.error('Error:', error);
      setMessages(prev => prev.filter(m => !m.isLoading));
      
      const errorMessage = {
        id: Date.now() + 2,
        type: 'assistant',
        content: '抱歉，系统暂时无法回答您的问题。请确保后端服务已启动并正常运行。'
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendQuestion(inputValue);
    }
  };

  const handleSkinImageUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (ev) => {
      setPreviewImage(ev.target.result);
    };
    reader.readAsDataURL(file);

    setSkinLoading(true);
    setSkinResult(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API_BASE_URL}/api/skin-analyze`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setSkinResult(response.data);

      if (response.data.emergency && response.data.emergency_alert) {
        setCurrentEmergency({
          is_emergency: true,
          level: response.data.emergency_alert.level,
          alerts: [{
            condition: response.data.primary_condition?.condition || '皮肤紧急情况',
            level: response.data.emergency_alert.level,
            matched_symptoms: response.data.visual_features || [],
            action: response.data.emergency_alert.action,
            departments: [response.data.department || '皮肤科'],
            possible_causes: []
          }],
          emergency_advice: response.data.emergency_alert.action
        });
        setEmergencyModalVisible(true);
      }
    } catch (error) {
      console.error('Skin analysis error:', error);
      setSkinResult({
        success: false,
        error: '图片分析失败，请确保后端服务已启动。' + (error.response?.data?.detail || '')
      });
    } finally {
      setSkinLoading(false);
    }
  };

  const handleDrugInteraction = async () => {
    const drugs = drugInputs.filter(d => d.trim());
    if (drugs.length < 2) return;

    setDrugLoading(true);
    setDrugResult(null);

    try {
      const response = await axios.post(`${API_BASE_URL}/api/drug-interaction`, {
        drugs: drugs
      });
      setDrugResult(response.data);
    } catch (error) {
      console.error('Drug interaction error:', error);
      setDrugResult({
        error: '查询失败，请确保后端服务已启动。' + (error.response?.data?.detail || '')
      });
    } finally {
      setDrugLoading(false);
    }
  };

  const addDrugInput = () => {
    if (drugInputs.length < 10) {
      setDrugInputs([...drugInputs, '']);
    }
  };

  const removeDrugInput = (index) => {
    if (drugInputs.length > 2) {
      setDrugInputs(drugInputs.filter((_, i) => i !== index));
    }
  };

  const updateDrugInput = (index, value) => {
    const newInputs = [...drugInputs];
    newInputs[index] = value;
    setDrugInputs(newInputs);
  };

  const showEvidenceDetail = (evidence) => {
    setCurrentEvidence(evidence);
    setEvidenceModalVisible(true);
  };

  const renderHighlightedText = (text) => {
    if (!text) return null;
    const parts = text.split(/<<(.+?)>>/g);
    return parts.map((part, idx) => {
      if (idx % 2 === 1) {
        return <mark key={idx} className="highlight-keyword">{part}</mark>;
      }
      return <span key={idx}>{part}</span>;
    });
  };

  const renderMessage = (message) => {
    if (message.isLoading) {
      return (
        <div key={message.id} className="message assistant">
          <div className="message-content">
            <div className="loading-dots">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        </div>
      );
    }

    return (
      <div key={message.id} className={`message ${message.type}`}>
        <div className="message-content">
          {message.type === 'assistant' && message.emergency && message.emergency.is_emergency && (
            <div className={`emergency-banner emergency-${message.emergency.level.toLowerCase()}`}>
              <AlertOutlined style={{ marginRight: 8, fontSize: 18 }} />
              <div>
                <div className="emergency-title">
                  {message.emergency.level === 'CRITICAL' ? '🚨 危急症状检测' : 
                   message.emergency.level === 'HIGH' ? '⚠️ 紧急症状检测' : '⚠ 注意'}
                </div>
                <div className="emergency-desc">
                  检测到疑似危急症状：{message.emergency.alerts.map(a => a.condition).join('、')}
                </div>
                <Button 
                  type="primary" 
                  danger={message.emergency.level === 'CRITICAL'}
                  size="small"
                  onClick={() => { setCurrentEmergency(message.emergency); setEmergencyModalVisible(true); }}
                  style={{ marginTop: 8 }}
                >
                  查看紧急处置建议
                </Button>
              </div>
            </div>
          )}

          {message.type === 'assistant' && message.intent && (
            <div className="intent-badge">
              <SearchOutlined style={{ marginRight: 5 }} />
              <span>意图识别：{intentMap[message.intent] || message.intent}</span>
              <span style={{ marginLeft: 8, opacity: 0.7 }}>
                ({(message.intentConfidence * 100).toFixed(1)}%)
              </span>
            </div>
          )}
          
          {message.type === 'assistant' && message.entities && message.entities.length > 0 && (
            <div style={{ marginBottom: 10 }}>
              {message.entities.map((entity, idx) => (
                <span key={idx} className={`entity-tag ${entity.is_rare ? 'entity-rare' : ''}`}>
                  {entity.text}
                  {entity.canonical && entity.canonical !== entity.text && 
                    <span style={{ opacity: 0.7 }}> → {entity.canonical}</span>
                  }
                  <span style={{ opacity: 0.6, marginLeft: 3 }}>
                    ({entity.type}{entity.is_rare ? '/罕见' : ''})
                  </span>
                  {entity.match_method === 'fuzzy' && 
                    <span style={{ opacity: 0.5, marginLeft: 3 }}>
                      模糊{((entity.fuzzy_score || 0) * 100).toFixed(0)}%
                    </span>
                  }
                  {entity.match_method === 'alias' && 
                    <span style={{ opacity: 0.5, marginLeft: 3 }}>别名</span>
                  }
                </span>
              ))}
            </div>
          )}
          
          <div className="answer-text">{message.content}</div>
          
          {message.type === 'assistant' && message.evidence && message.evidence.length > 0 && (
            <div className="evidence-section">
              <div className="evidence-header">
                <SafetyOutlined style={{ marginRight: 5, color: '#52c41a' }} />
                证据溯源
              </div>
              {message.evidence.filter(ev => ev.node_type !== 'System').slice(0, 3).map((ev, idx) => (
                <div key={idx} className={`evidence-item ${ev.is_rare ? 'evidence-rare' : ''}`}>
                  <div className="evidence-source">
                    <FileTextOutlined style={{ marginRight: 5 }} />
                    [{ev.source}] {ev.node_type}
                    {ev.is_rare && <span className="rare-badge">罕见病</span>}
                  </div>
                  <div style={{ marginTop: 5, color: '#666' }}>{ev.content}</div>
                  <div className="evidence-meta">
                    <span>置信度：{(ev.confidence * 100).toFixed(1)}%</span>
                    {ev.paragraph_location && (
                      <span style={{ marginLeft: 10 }}>
                        定位：第{ev.paragraph_location.paragraph_index + 1}段 · {ev.paragraph_location.section}
                      </span>
                    )}
                  </div>
                  {(ev.highlighted_text || ev.paragraph_location) && (
                    <Button 
                      type="link" 
                      size="small"
                      onClick={() => showEvidenceDetail(ev)}
                      style={{ padding: 0, marginTop: 5 }}
                    >
                      📖 查看原文定位与高亮
                    </Button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  };

  const renderQATab = () => (
    <div className="chat-container">
      <div className="chat-messages">
        {messages.length === 0 && (
          <div style={{ textAlign: 'center', padding: '40px 20px', color: '#999' }}>
            <MedicineBoxOutlined style={{ fontSize: 64, marginBottom: 20, opacity: 0.5 }} />
            <p style={{ fontSize: '1.1rem' }}>您好，我是您的智能医疗助手</p>
            <p>支持常见病与罕见病查询、紧急症状检测</p>
            <p style={{ marginTop: 10, fontSize: '0.9rem' }}>
              如遇紧急情况请直接拨打 <span style={{ color: '#d4380d', fontWeight: 'bold' }}>120</span>
            </p>
          </div>
        )}
        
        {messages.map(renderMessage)}
        <div ref={messagesEndRef} />
      </div>
      
      <div className="chat-input-container">
        <div className="quick-questions">
          {quickQuestions.map((q, idx) => (
            <button
              key={idx}
              className="quick-btn"
              onClick={() => sendQuestion(q)}
              disabled={isLoading}
            >
              {q}
            </button>
          ))}
        </div>
        
        <div className="input-area">
          <TextArea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="请输入您的健康问题（如遇胸痛、呼吸困难等紧急症状，系统将自动预警）..."
            autoSize={{ minRows: 1, maxRows: 4 }}
            disabled={isLoading}
          />
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={() => sendQuestion(inputValue)}
            loading={isLoading}
            size="large"
          >
            发送
          </Button>
        </div>
      </div>
    </div>
  );

  const renderSkinTab = () => (
    <div className="feature-panel">
      <div className="feature-panel-header">
        <CameraOutlined style={{ fontSize: 24, marginRight: 10, color: '#1890ff' }} />
        <div>
          <h3>皮肤照片症状识别</h3>
          <p style={{ fontSize: '0.85rem', color: '#999', margin: 0 }}>
            上传皮肤照片，AI辅助识别可能的皮肤问题
          </p>
        </div>
      </div>
      
      <div className="skin-upload-area">
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleSkinImageUpload}
          accept="image/jpeg,image/png,image/webp,image/bmp"
          style={{ display: 'none' }}
        />
        <div 
          className="upload-zone"
          onClick={() => fileInputRef.current?.click()}
        >
          {previewImage ? (
            <img src={previewImage} alt="preview" className="preview-image" />
          ) : (
            <div className="upload-placeholder">
              <CameraOutlined style={{ fontSize: 48, color: '#bbb' }} />
              <p style={{ marginTop: 16, color: '#999' }}>点击上传皮肤照片</p>
              <p style={{ fontSize: '0.8rem', color: '#ccc' }}>支持 JPG/PNG/WebP/BMP，最大10MB</p>
            </div>
          )}
        </div>
        {previewImage && (
          <Button 
            onClick={() => fileInputRef.current?.click()}
            style={{ marginTop: 10 }}
            loading={skinLoading}
          >
            重新上传分析
          </Button>
        )}
      </div>

      {skinLoading && (
        <div style={{ textAlign: 'center', padding: 20 }}>
          <div className="loading-dots">
            <span></span><span></span><span></span>
          </div>
          <p style={{ marginTop: 10, color: '#999' }}>正在分析图片...</p>
        </div>
      )}

      {skinResult && skinResult.success && (
        <div className="skin-result">
          <div className={`severity-badge severity-${skinResult.severity}`}>
            {skinResult.severity === 'severe' ? '🚨 需紧急就医' :
             skinResult.severity === 'moderate' ? '⚠️ 建议就医' : 'ℹ️ 可观察'}
          </div>
          
          <h4>分析结果：{skinResult.primary_condition?.condition}</h4>
          <p className="skin-confidence">
            置信度：{((skinResult.primary_condition?.confidence || 0) * 100).toFixed(1)}%
          </p>
          
          <div className="skin-detail-section">
            <div className="detail-label">描述</div>
            <p>{skinResult.description}</p>
          </div>
          
          <div className="skin-detail-section">
            <div className="detail-label">视觉特征</div>
            <div>
              {(skinResult.visual_features || []).map((f, i) => (
                <Tag key={i} color="blue" style={{ marginBottom: 4 }}>{f}</Tag>
              ))}
            </div>
          </div>
          
          <div className="skin-detail-section">
            <div className="detail-label">建议科室</div>
            <p>{skinResult.department}</p>
          </div>
          
          <div className="skin-detail-section">
            <div className="detail-label">处置建议</div>
            <p>{skinResult.advice}</p>
          </div>

          {skinResult.differential && skinResult.differential.length > 1 && (
            <div className="skin-detail-section">
              <div className="detail-label">鉴别诊断</div>
              {skinResult.differential.slice(1).map((d, i) => (
                <div key={i} style={{ marginBottom: 4 }}>
                  {d.condition} ({(d.confidence * 100).toFixed(1)}%)
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {skinResult && !skinResult.success && (
        <div className="skin-error">
          <WarningOutlined style={{ marginRight: 8, color: '#ff4d4f' }} />
          {skinResult.error}
        </div>
      )}
    </div>
  );

  const renderDrugTab = () => (
    <div className="feature-panel">
      <div className="feature-panel-header">
        <InteractionOutlined style={{ fontSize: 24, marginRight: 10, color: '#722ed1' }} />
        <div>
          <h3>药品相互作用查询</h3>
          <p style={{ fontSize: '0.85rem', color: '#999', margin: 0 }}>
            输入多种药物，查询联合用药风险
          </p>
        </div>
      </div>
      
      <div className="drug-input-area">
        <p className="drug-input-label">请输入需要查询的药物（至少2种，最多10种）：</p>
        {drugInputs.map((drug, idx) => (
          <div key={idx} className="drug-input-row">
            <span className="drug-number">{idx + 1}</span>
            <Input
              value={drug}
              onChange={(e) => updateDrugInput(idx, e.target.value)}
              placeholder="输入药物名称，如：布洛芬"
              size="large"
            />
            {drugInputs.length > 2 && (
              <Button 
                type="text" 
                danger 
                icon={<DeleteOutlined />}
                onClick={() => removeDrugInput(idx)}
              />
            )}
          </div>
        ))}
        <div className="drug-actions">
          <Button 
            type="dashed" 
            icon={<PlusOutlined />}
            onClick={addDrugInput}
            disabled={drugInputs.length >= 10}
          >
            添加药物
          </Button>
          <Button 
            type="primary" 
            icon={<InteractionOutlined />}
            onClick={handleDrugInteraction}
            loading={drugLoading}
            disabled={drugInputs.filter(d => d.trim()).length < 2}
            style={{ background: '#722ed1', borderColor: '#722ed1' }}
          >
            查询相互作用
          </Button>
        </div>
      </div>

      {drugResult && !drugResult.error && (
        <div className="drug-result">
          <div className={`risk-badge risk-${drugResult.overall_risk?.level}`}>
            {drugResult.overall_risk?.level === 'high' ? '🚫 高风险' :
             drugResult.overall_risk?.level === 'moderate' ? '⚠️ 中等风险' :
             drugResult.overall_risk?.level === 'low' ? 'ℹ️ 低风险' : '✅ 安全'}
          </div>
          
          <div className="risk-description">{drugResult.overall_risk?.description}</div>
          
          <div className="drug-summary">
            <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}>
              {drugResult.summary}
            </pre>
          </div>
          
          <div className="drug-recommendation">
            <strong>综合建议：</strong>{drugResult.recommendation}
          </div>
        </div>
      )}

      {drugResult && drugResult.error && (
        <div className="skin-error">
          <WarningOutlined style={{ marginRight: 8, color: '#ff4d4f' }} />
          {drugResult.error}
        </div>
      )}
    </div>
  );

  return (
    <div className="app-container">
      <div className="header">
        <h1><MedicineBoxOutlined /> 医疗知识问答系统</h1>
        <p>基于知识图谱和AI技术，为您提供专业的医疗健康咨询</p>
      </div>

      <div className="tab-bar">
        <button 
          className={`tab-btn ${activeTab === 'qa' ? 'active' : ''}`}
          onClick={() => setActiveTab('qa')}
        >
          <SearchOutlined /> 智能问答
        </button>
        <button 
          className={`tab-btn ${activeTab === 'skin' ? 'active' : ''}`}
          onClick={() => setActiveTab('skin')}
        >
          <CameraOutlined /> 皮肤识别
        </button>
        <button 
          className={`tab-btn ${activeTab === 'drug' ? 'active' : ''}`}
          onClick={() => setActiveTab('drug')}
        >
          <InteractionOutlined /> 药品交互
        </button>
      </div>
      
      {activeTab === 'qa' && renderQATab()}
      {activeTab === 'skin' && renderSkinTab()}
      {activeTab === 'drug' && renderDrugTab()}

      <Modal
        title={
          <div style={{ display: 'flex', alignItems: 'center', color: '#d4380d' }}>
            <WarningOutlined style={{ marginRight: 8, fontSize: 20 }} />
            医疗免责声明
          </div>
        }
        open={disclaimerVisible}
        onOk={handleDisclaimerAgree}
        onCancel={handleDisclaimerCancel}
        maskClosable={false}
        closable={false}
        width={560}
        footer={[
          <Button key="cancel" onClick={handleDisclaimerCancel}>暂不使用</Button>,
          <Button 
            key="agree" type="primary" onClick={handleDisclaimerAgree}
            style={{ background: '#52c41a', borderColor: '#52c41a' }}
          >
            我已阅读并同意，继续使用
          </Button>,
        ]}
      >
        <div className="disclaimer-modal-content">
          <div className="disclaimer-warning-banner">
            <WarningOutlined style={{ fontSize: 24, color: '#fa8c16' }} />
            <span>本系统不提供医学诊断，如有紧急情况请拨打120</span>
          </div>
          <div className="disclaimer-text">
            {DISCLAIMER_TEXT.split('\n').map((line, idx) => (
              <p key={idx}>{line}</p>
            ))}
          </div>
          <div className="disclaimer-checkbox-area">
            <Checkbox checked={true} onChange={() => {}} style={{ color: '#666' }}>
              我已仔细阅读以上免责声明，并理解本系统仅提供参考信息
            </Checkbox>
          </div>
        </div>
      </Modal>

      <Modal
        title={
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <FileTextOutlined style={{ marginRight: 8, color: '#1890ff' }} />
            证据原文定位与高亮
          </div>
        }
        open={evidenceModalVisible}
        onCancel={() => setEvidenceModalVisible(false)}
        footer={[<Button key="close" onClick={() => setEvidenceModalVisible(false)}>关闭</Button>]}
        width={640}
      >
        {currentEvidence && (
          <div className="evidence-detail-modal">
            <div className="evidence-detail-meta">
              <div className="meta-item">
                <span className="meta-label">来源：</span><span>{currentEvidence.source}</span>
              </div>
              <div className="meta-item">
                <span className="meta-label">节点类型：</span><span>{currentEvidence.node_type}</span>
              </div>
              <div className="meta-item">
                <span className="meta-label">置信度：</span>
                <span>{((currentEvidence.confidence || 0) * 100).toFixed(1)}%</span>
              </div>
              {currentEvidence.paragraph_location && (
                <div className="meta-item">
                  <span className="meta-label">段落定位：</span>
                  <span>第{currentEvidence.paragraph_location.paragraph_index + 1}段 · {currentEvidence.paragraph_location.section}</span>
                </div>
              )}
            </div>
            {currentEvidence.highlighted_text && (
              <div className="highlighted-text-section">
                <div className="highlight-label">原文高亮（关键词标黄）：</div>
                <div className="highlighted-text-content">
                  {renderHighlightedText(currentEvidence.highlighted_text)}
                </div>
              </div>
            )}
            {currentEvidence.original_text && (
              <div className="original-text-section">
                <div className="original-label">完整原文：</div>
                <div className="original-text-content">{currentEvidence.original_text}</div>
              </div>
            )}
          </div>
        )}
      </Modal>

      <Modal
        title={
          <div style={{ display: 'flex', alignItems: 'center', color: '#d4380d' }}>
            <AlertOutlined style={{ marginRight: 8, fontSize: 22 }} />
            {currentEmergency?.level === 'CRITICAL' ? '🚨 危急症状警报' : '⚠️ 紧急就医提醒'}
          </div>
        }
        open={emergencyModalVisible}
        onCancel={() => setEmergencyModalVisible(false)}
        width={560}
        footer={[
          <Button key="close" onClick={() => setEmergencyModalVisible(false)}>
            我已了解
          </Button>,
          <Button 
            key="call120" type="primary" danger
            onClick={() => { window.open('tel:120'); }}
            style={{ background: '#ff4d4f', borderColor: '#ff4d4f' }}
          >
            <PhoneOutlined /> 拨打120
          </Button>,
        ]}
      >
        {currentEmergency && (
          <div className="emergency-modal-content">
            <div className={`emergency-level-banner level-${(currentEmergency.level || '').toLowerCase()}`}>
              {currentEmergency.level === 'CRITICAL' ? '🚨 危急 — 请立即就医！' :
               currentEmergency.level === 'HIGH' ? '⚠️ 紧急 — 请尽快就医！' :
               '⚠ 注意 — 建议尽早就诊'}
            </div>
            
            {currentEmergency.alerts && currentEmergency.alerts.map((alert, idx) => (
              <div key={idx} className="emergency-alert-item">
                <h4>{alert.condition}</h4>
                <p><strong>匹配症状：</strong>{alert.matched_symptoms?.join('、')}</p>
                <p><strong>紧急处置：</strong>{alert.action}</p>
                <p><strong>建议科室：</strong>{alert.departments?.join('、')}</p>
                {alert.possible_causes && alert.possible_causes.length > 0 && (
                  <p><strong>可能原因：</strong>{alert.possible_causes.join('、')}</p>
                )}
              </div>
            ))}
            
            {currentEmergency.emergency_advice && (
              <div className="emergency-advice-box">
                {currentEmergency.emergency_advice}
              </div>
            )}
            
            <div className="emergency-call-banner">
              <PhoneOutlined style={{ marginRight: 8 }} />
              如遇紧急情况，请立即拨打 <strong>120</strong> 急救电话
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}

export default App;
