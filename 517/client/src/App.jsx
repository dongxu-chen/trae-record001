import { useState, useEffect, useCallback } from 'react';
import RuleTable from './components/RuleTable.jsx';
import DataPreview from './components/DataPreview.jsx';
import BatchPreview from './components/BatchPreview.jsx';
import StrategyTemplates from './components/StrategyTemplates.jsx';
import PermissionSelector from './components/PermissionSelector.jsx';
import AuditLogs from './components/AuditLogs.jsx';

const defaultTemplates = [
  {
    id: 'financial',
    name: '金融安全级',
    description: '适用于金融行业，高安全要求',
    icon: '🏦',
    color: '#dc2626',
    rules: {
      phone: { enabled: true, method: 'mask', pattern: 'adaptive', keepStart: 3, keepEnd: 2, label: '手机号码' },
      idCard: { enabled: true, method: 'mask', pattern: 'adaptive', keepStart: 3, keepEnd: 2, label: '身份证号' },
      email: { enabled: true, method: 'mask', pattern: 'adaptive', keepStart: 1, keepEnd: 0, label: '邮箱地址' },
      name: { enabled: true, method: 'mask', pattern: 'adaptive', keepStart: 1, keepEnd: 0, label: '姓名' },
      address: { enabled: true, method: 'truncate', maxLength: 6, label: '地址' }
    }
  },
  {
    id: 'enterprise',
    name: '企业标准级',
    description: '适用于企业内部使用',
    icon: '🏢',
    color: '#2563eb',
    rules: {
      phone: { enabled: true, method: 'mask', pattern: 'adaptive', keepStart: 3, keepEnd: 4, label: '手机号码' },
      idCard: { enabled: true, method: 'mask', pattern: 'adaptive', keepStart: 6, keepEnd: 4, label: '身份证号' },
      email: { enabled: true, method: 'mask', pattern: 'adaptive', keepStart: 2, keepEnd: 0, label: '邮箱地址' },
      name: { enabled: false, method: 'mask', pattern: 'adaptive', keepStart: 1, keepEnd: 1, label: '姓名' },
      address: { enabled: true, method: 'truncate', maxLength: 10, label: '地址' }
    }
  },
  {
    id: 'basic',
    name: '基础保护级',
    description: '适用于一般数据保护场景',
    icon: '🛡️',
    color: '#059669',
    rules: {
      phone: { enabled: true, method: 'mask', pattern: 'adaptive', keepStart: 3, keepEnd: 4, label: '手机号码' },
      idCard: { enabled: true, method: 'hash', hashAlgorithm: 'md5', hashSalt: 'basic-salt', label: '身份证号' },
      email: { enabled: true, method: 'mask', pattern: 'adaptive', keepStart: 3, keepEnd: 2, label: '邮箱地址' },
      name: { enabled: false, method: 'mask', pattern: 'adaptive', keepStart: 1, keepEnd: 1, label: '姓名' },
      address: { enabled: false, method: 'truncate', maxLength: 15, label: '地址' }
    }
  },
  {
    id: 'privacy',
    name: '隐私合规级',
    description: '符合GDPR等隐私法规要求',
    icon: '🔒',
    color: '#7c3aed',
    rules: {
      phone: { enabled: true, method: 'hash', hashAlgorithm: 'sha256', hashSalt: 'privacy-2024', label: '手机号码' },
      idCard: { enabled: true, method: 'hash', hashAlgorithm: 'sha256', hashSalt: 'privacy-2024', label: '身份证号' },
      email: { enabled: true, method: 'mask', pattern: 'adaptive', keepStart: 2, keepEnd: 0, label: '邮箱地址' },
      name: { enabled: true, method: 'hash', hashAlgorithm: 'sha256', hashSalt: 'privacy-2024', label: '姓名' },
      address: { enabled: true, method: 'truncate', maxLength: 4, label: '地址' }
    }
  },
  {
    id: 'test',
    name: '测试开发级',
    description: '适用于开发测试环境',
    icon: '🧪',
    color: '#f59e0b',
    rules: {
      phone: { enabled: true, method: 'shuffle', label: '手机号码' },
      idCard: { enabled: true, method: 'shuffle', label: '身份证号' },
      email: { enabled: true, method: 'replace', replacement: '*', pattern: 'adaptive', label: '邮箱地址' },
      name: { enabled: false, method: 'mask', pattern: 'adaptive', keepStart: 1, keepEnd: 1, label: '姓名' },
      address: { enabled: false, method: 'truncate', maxLength: 20, label: '地址' }
    }
  }
];

const defaultPermissions = [
  { value: 'admin', level: 0, label: '管理员', description: '完全可见，不脱敏' },
  { value: 'senior', level: 1, label: '高级用户', description: '轻度脱敏，保留较多信息' },
  { value: 'normal', level: 2, label: '普通用户', description: '中度脱敏' },
  { value: 'guest', level: 3, label: '访客', description: '高度脱敏，仅保留格式' }
];

const defaultMethods = [
  { value: 'mask', label: '掩码脱敏', description: '自适应掩码，按输入长度动态调整' },
  { value: 'replace', label: '替换脱敏', description: '自定义替换字符' },
  { value: 'hash', label: '哈希脱敏', description: '不可逆哈希加密，支持盐值' },
  { value: 'truncate', label: '截断脱敏', description: '截断超出长度的内容' },
  { value: 'shuffle', label: '打乱脱敏', description: '随机打乱字符顺序' }
];

const defaultPatterns = [
  { value: 'adaptive', label: '自适应' },
  { value: 'phone', label: '手机号模式' },
  { value: 'idCard', label: '身份证模式' },
  { value: 'email', label: '邮箱模式' },
  { value: 'all', label: '全部掩码' }
];

const App = () => {
  const [rules, setRules] = useState({});
  const [methods, setMethods] = useState(defaultMethods);
  const [patterns, setPatterns] = useState(defaultPatterns);
  const [templates, setTemplates] = useState(defaultTemplates);
  const [permissions, setPermissions] = useState(defaultPermissions);
  const [activeTab, setActiveTab] = useState('single');
  const [activeMainTab, setActiveMainTab] = useState('config');
  const [currentTemplate, setCurrentTemplate] = useState('enterprise');
  const [currentPermission, setCurrentPermission] = useState('normal');
  const [currentUser, setCurrentUser] = useState({ id: 'normal_001', name: '李员工', role: 'normal' });
  const [auditLogs, setAuditLogs] = useState([]);
  const [auditLoading, setAuditLoading] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const [rulesRes, templatesRes, permissionsRes] = await Promise.all([
          fetch('/api/rules/default'),
          fetch('/api/templates'),
          fetch('/api/permissions')
        ]).catch(() => [null, null, null]);

        const rulesData = rulesRes ? await rulesRes.json() : null;
        const templatesData = templatesRes ? await templatesRes.json() : null;
        const permissionsData = permissionsRes ? await permissionsRes.json() : null;

        if (rulesData) {
          const enhancedRules = Object.fromEntries(
            Object.entries(rulesData).map(([key, rule]) => [
              key,
              {
                ...rule,
                pattern: rule.pattern || 'adaptive',
                keepStart: rule.keepStart ?? (key === 'phone' ? 3 : key === 'idCard' ? 6 : 2),
                keepEnd: rule.keepEnd ?? (key === 'phone' ? 4 : key === 'idCard' ? 4 : key === 'email' ? 0 : 2),
                hashSalt: rule.hashSalt || '',
                hashAlgorithm: rule.hashAlgorithm || 'md5',
                replacement: rule.replacement || '*',
                maxLength: rule.maxLength || 10
              }
            ])
          );
          setRules(enhancedRules);
        } else {
          setRules({
            phone: {
              enabled: true,
              method: 'mask',
              pattern: 'adaptive',
              label: '手机号码',
              placeholder: '13800138000',
              keepStart: 3,
              keepEnd: 4,
              hashSalt: '',
              hashAlgorithm: 'md5',
              replacement: '*',
              maxLength: 10
            },
            idCard: {
              enabled: true,
              method: 'mask',
              pattern: 'adaptive',
              label: '身份证号',
              placeholder: '110101199001011234',
              keepStart: 6,
              keepEnd: 4,
              hashSalt: '',
              hashAlgorithm: 'md5',
              replacement: '*',
              maxLength: 10
            },
            email: {
              enabled: true,
              method: 'mask',
              pattern: 'adaptive',
              label: '邮箱地址',
              placeholder: 'example@email.com',
              keepStart: 2,
              keepEnd: 0,
              hashSalt: '',
              hashAlgorithm: 'md5',
              replacement: '*',
              maxLength: 10
            },
            name: {
              enabled: false,
              method: 'mask',
              pattern: 'adaptive',
              label: '姓名',
              placeholder: '张三',
              keepStart: 1,
              keepEnd: 0,
              hashSalt: '',
              hashAlgorithm: 'md5',
              replacement: '*',
              maxLength: 10
            },
            address: {
              enabled: false,
              method: 'truncate',
              label: '地址',
              placeholder: '北京市朝阳区某某街道123号',
              keepStart: 2,
              keepEnd: 2,
              hashSalt: '',
              hashAlgorithm: 'md5',
              replacement: '*',
              maxLength: 10
            }
          });
        }

        if (templatesData) setTemplates(templatesData);
        if (permissionsData) setPermissions(permissionsData);
      } catch (error) {
        console.error('获取配置失败:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchConfig();
    fetchAuditLogs();
  }, []);

  const fetchAuditLogs = async () => {
    try {
      setAuditLoading(true);
      const res = await fetch('/api/audit/logs?limit=50');
      if (res.ok) {
        const data = await res.json();
        setAuditLogs(data.logs || []);
      }
    } catch (error) {
      console.error('获取审计日志失败:', error);
    } finally {
      setAuditLoading(false);
    }
  };

  const updateRule = useCallback((fieldKey, updates) => {
    setRules(prev => ({
      ...prev,
      [fieldKey]: {
        ...prev[fieldKey],
        ...updates
      }
    }));
    setCurrentTemplate(null);
  }, []);

  const toggleRule = useCallback((fieldKey) => {
    setRules(prev => ({
      ...prev,
      [fieldKey]: {
        ...prev[fieldKey],
        enabled: !prev[fieldKey].enabled
      }
    }));
  }, []);

  const batchUpdateRules = useCallback((fieldKeys, updates) => {
    setRules(prev => {
      const newRules = { ...prev };
      fieldKeys.forEach(key => {
        newRules[key] = {
          ...newRules[key],
          ...updates
        };
      });
      return newRules;
    });
  }, []);

  const applyTemplate = useCallback((template) => {
    setCurrentTemplate(template.id);
    
    setRules(prev => {
      const newRules = { ...prev };
      Object.entries(template.rules).forEach(([field, templateRule]) => {
        if (newRules[field]) {
          newRules[field] = {
            ...newRules[field],
            ...templateRule
          };
        }
      });
      return newRules;
    });

    const newLog = {
      id: Date.now() + Math.random().toString(36).substr(2, 9),
      timestamp: new Date().toISOString(),
      action: 'apply_template',
      userId: currentUser.id,
      userName: currentUser.name,
      permission: currentPermission,
      templateId: template.id,
      templateName: template.name,
      sensitiveFields: Object.entries(template.rules).filter(([_, r]) => r.enabled).map(([f]) => f)
    };
    setAuditLogs(prev => [newLog, ...prev].slice(0, 100));
  }, [currentUser, currentPermission]);

  const addAuditLog = useCallback((log) => {
    const newLog = {
      id: Date.now() + Math.random().toString(36).substr(2, 9),
      timestamp: new Date().toISOString(),
      ...log,
      userId: currentUser.id,
      userName: currentUser.name,
      permission: currentPermission
    };
    setAuditLogs(prev => [newLog, ...prev].slice(0, 100));
  }, [currentUser, currentPermission]);

  if (loading) {
    return (
      <div className="app">
        <div className="app-header">
          <h1>数据脱敏预览组件</h1>
          <p>配置脱敏规则，实时预览脱敏效果</p>
        </div>
        <div className="loading">
          <div className="spinner"></div>
          加载中...
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      <div className="app-header">
        <h1>🔒 数据脱敏预览组件</h1>
        <p>策略模板 · 动态脱敏 · 权限控制 · 审计追踪</p>
      </div>

      <div className="main-tabs">
        <button
          className={`main-tab ${activeMainTab === 'config' ? 'active' : ''}`}
          onClick={() => setActiveMainTab('config')}
        >
          ⚙️ 规则配置
        </button>
        <button
          className={`main-tab ${activeMainTab === 'permission' ? 'active' : ''}`}
          onClick={() => setActiveMainTab('permission')}
        >
          🔐 权限模拟
        </button>
        <button
          className={`main-tab ${activeMainTab === 'audit' ? 'active' : ''}`}
          onClick={() => {
            setActiveMainTab('audit');
            fetchAuditLogs();
          }}
        >
          📜 审计日志
        </button>
      </div>

      {activeMainTab === 'config' && (
        <>
          <div className="template-section">
            <div className="card full-width">
              <div className="card-body">
                <StrategyTemplates
                  templates={templates}
                  currentTemplate={currentTemplate}
                  onApplyTemplate={applyTemplate}
                />
              </div>
            </div>
          </div>

          <div className="config-section">
            <div className="card full-width">
              <div className="card-header">
                <h2>⚙️ 字段规则配置</h2>
              </div>
              <div className="card-body">
                <RuleTable
                  rules={rules}
                  methods={methods}
                  patterns={patterns}
                  onToggle={toggleRule}
                  onUpdate={updateRule}
                  onBatchUpdate={batchUpdateRules}
                />
              </div>
            </div>
          </div>

          <div className="preview-section-full">
            <div className="card full-width">
              <div className="card-header">
                <h2>👁️ 脱敏效果预览</h2>
                <span className="permission-badge">
                  当前权限: {permissions.find(p => p.value === currentPermission)?.label || '普通用户'}
                </span>
              </div>
              <div className="card-body">
                <div className="tab-container">
                  <button
                    className={`tab-btn ${activeTab === 'single' ? 'active' : ''}`}
                    onClick={() => setActiveTab('single')}
                  >
                    单条数据
                  </button>
                  <button
                    className={`tab-btn ${activeTab === 'batch' ? 'active' : ''}`}
                    onClick={() => setActiveTab('batch')}
                  >
                    批量数据
                  </button>
                </div>

                {activeTab === 'single' ? (
                  <DataPreview 
                    rules={rules} 
                    permission={currentPermission}
                    onAuditLog={addAuditLog}
                  />
                ) : (
                  <BatchPreview 
                    rules={rules} 
                    permission={currentPermission}
                    onAuditLog={addAuditLog}
                  />
                )}
              </div>
            </div>
          </div>
        </>
      )}

      {activeMainTab === 'permission' && (
        <div className="card full-width">
          <div className="card-body">
            <PermissionSelector
              permissions={permissions}
              currentPermission={currentPermission}
              onPermissionChange={setCurrentPermission}
              currentUser={currentUser}
              onUserChange={setCurrentUser}
            />
          </div>
        </div>
      )}

      {activeMainTab === 'audit' && (
        <div className="card full-width">
          <div className="card-body">
            <AuditLogs
              logs={auditLogs}
              loading={auditLoading}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default App;
