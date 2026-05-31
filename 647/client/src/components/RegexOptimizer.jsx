import React, { useMemo, useState } from 'react';
import { optimizePattern, evaluatePerformance, getPasswordStrength } from '../utils/regexEngine';

const PerformanceBar = ({ score, grade, complexity }) => {
  const getColor = () => {
    if (score >= 90) return '#22c55e';
    if (score >= 75) return '#84cc16';
    if (score >= 60) return '#f59e0b';
    if (score >= 40) return '#f97316';
    return '#ef4444';
  };

  const getBgColor = () => {
    if (score >= 90) return '#22c55e20';
    if (score >= 75) return '#84cc1620';
    if (score >= 60) return '#f59e0b20';
    if (score >= 40) return '#f9731620';
    return '#ef444420';
  };

  return (
    <div className="performance-bar-container">
      <div className="performance-header">
        <div className="performance-score" style={{ color: getColor() }}>
          {score}
        </div>
        <div className="performance-info">
          <div className="performance-grade" style={{ background: getBgColor(), color: getColor() }}>
            {grade}
          </div>
          <div className="performance-complexity">{complexity}</div>
        </div>
      </div>
      <div className="performance-bar">
        <div
          className="performance-bar-fill"
          style={{
            width: `${score}%`,
            background: `linear-gradient(90deg, ${getColor()}90, ${getColor()})`
          }}
        />
      </div>
    </div>
  );
};

const FactorItem = ({ factor }) => {
  const isPositive = factor.impact < 0;
  const isNegative = factor.impact > 0;

  return (
    <div className={`factor-item ${isPositive ? 'positive' : ''} ${isNegative ? 'negative' : ''}`}>
      <div className="factor-header">
        <span className="factor-name">{factor.name}</span>
        <span className="factor-count">×{factor.count}</span>
      </div>
      <div className="factor-desc">{factor.description}</div>
      <div className="factor-impact">
        {isPositive ? '📈' : isNegative ? '📉' : '📊'}
        <span>
          {isPositive ? '性能提升' : isNegative ? '性能下降' : '影响'}: {Math.abs(factor.impact)}%
        </span>
      </div>
    </div>
  );
};

const OptimizationItem = ({ optimization, onApply }) => {
  return (
    <div className="optimization-item">
      <div className="optimization-header">
        <span className="optimization-icon">💡</span>
        <span className="optimization-name">{optimization.name}</span>
      </div>
      <div className="optimization-desc">{optimization.description}</div>
      <div className="optimization-code">
        <div className="code-original">
          <span className="code-label">原始:</span>
          <code>{optimization.original}</code>
        </div>
        <div className="code-arrow">→</div>
        <div className="code-improved">
          <span className="code-label">优化:</span>
          <code>{optimization.improved}</code>
        </div>
      </div>
      <div className="optimization-footer">
        <span className="optimization-improvement">✨ {optimization.improvement}</span>
        <button
          className="btn btn-sm btn-primary"
          onClick={onApply}
        >
          应用优化
        </button>
      </div>
    </div>
  );
};

const RecommendationItem = ({ recommendation }) => {
  const getIcon = () => {
    switch (recommendation.type) {
      case 'warning': return '⚠️';
      case 'success': return '✅';
      case 'info':
      default: return 'ℹ️';
    }
  };

  const getStyle = () => {
    switch (recommendation.type) {
      case 'warning':
        return { background: '#fef3c7', borderColor: '#f59e0b', color: '#92400e' };
      case 'success':
        return { background: '#dcfce7', borderColor: '#22c55e', color: '#166534' };
      case 'info':
      default:
        return { background: '#dbeafe', borderColor: '#3b82f6', color: '#1e40af' };
    }
  };

  return (
    <div className="recommendation-item" style={getStyle()}>
      <span className="recommendation-icon">{getIcon()}</span>
      <span className="recommendation-text">{recommendation.message}</span>
    </div>
  );
};

const PasswordStrengthChecker = () => {
  const [password, setPassword] = useState('');
  const strength = useMemo(() => getPasswordStrength(password), [password]);

  return (
    <div className="password-strength-checker">
      <div className="section-header">
        <span className="section-icon">🔐</span>
        <span className="section-title">密码强度检测</span>
      </div>
      <input
        type="text"
        className="password-input"
        placeholder="输入密码进行强度检测..."
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />
      {password && (
        <div className="password-result">
          <div className="password-score-bar">
            <div
              className="password-score-fill"
              style={{
                width: `${strength.score}%`,
                background: strength.color
              }}
            />
          </div>
          <div className="password-score-info">
            <span className="password-label" style={{ color: strength.color }}>
              {strength.label}
            </span>
            <span className="password-score">{strength.score}/100</span>
          </div>
          <div className="password-checks">
            {strength.checks.map((check, i) => (
              <span key={i} className="check-item">✓ {check}</span>
            ))}
          </div>
          <div className="password-suggestions">
            <div className="suggestions-title">建议改进：</div>
            {strength.suggestions.map((suggestion, i) => (
              <div key={i} className={`suggestion-item ${suggestion.met ? 'met' : ''}`}>
                {suggestion.met ? '✅' : '⬜'} {suggestion.text}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

const RegexOptimizer = ({ pattern, testText, onApplyOptimization }) => {
  const [activeTab, setActiveTab] = useState('performance');

  const optimizationResult = useMemo(() => {
    return optimizePattern(pattern);
  }, [pattern]);

  const performanceResult = useMemo(() => {
    return evaluatePerformance(pattern, testText);
  }, [pattern, testText]);

  const handleApplyOptimization = (optimization) => {
    if (onApplyOptimization) {
      onApplyOptimization(optimization, optimizationResult.optimizedPattern);
    }
  };

  const handleApplyAllOptimizations = () => {
    if (onApplyOptimization && optimizationResult.canOptimize) {
      onApplyOptimization(null, optimizationResult.optimizedPattern);
    }
  };

  return (
    <div className="regex-optimizer">
      <div className="optimizer-tabs">
        <button
          className={`optimizer-tab ${activeTab === 'performance' ? 'active' : ''}`}
          onClick={() => setActiveTab('performance')}
        >
          ⚡ 性能评估
        </button>
        <button
          className={`optimizer-tab ${activeTab === 'optimize' ? 'active' : ''}`}
          onClick={() => setActiveTab('optimize')}
        >
          💡 表达式优化
          {optimizationResult.canOptimize && (
            <span className="badge">{optimizationResult.optimizations.length}</span>
          )}
        </button>
        <button
          className={`optimizer-tab ${activeTab === 'password' ? 'active' : ''}`}
          onClick={() => setActiveTab('password')}
        >
          🔐 密码检测
        </button>
      </div>

      <div className="optimizer-content">
        {activeTab === 'performance' && (
          <div className="performance-section">
            <div className="section-header">
              <span className="section-icon">⚡</span>
              <span className="section-title">性能评估</span>
            </div>

            {pattern ? (
              <>
                <PerformanceBar
                  score={performanceResult.score}
                  grade={performanceResult.grade}
                  complexity={performanceResult.complexity}
                />

                <div className="performance-metrics">
                  <div className="metric-item">
                    <span className="metric-label">预计耗时</span>
                    <span className="metric-value">
                      ~{performanceResult.estimatedTime.toFixed(3)}ms
                    </span>
                  </div>
                  <div className="metric-item">
                    <span className="metric-label">表达式长度</span>
                    <span className="metric-value">{performanceResult.patternLength} 字符</span>
                  </div>
                </div>

                {performanceResult.factors.length > 0 && (
                  <div className="factors-section">
                    <div className="subsection-title">影响因素分析</div>
                    <div className="factors-list">
                      {performanceResult.factors.map((factor, index) => (
                        <FactorItem key={index} factor={factor} />
                      ))}
                    </div>
                  </div>
                )}

                {performanceResult.recommendations.length > 0 && (
                  <div className="recommendations-section">
                    <div className="subsection-title">优化建议</div>
                    <div className="recommendations-list">
                      {performanceResult.recommendations.map((rec, index) => (
                        <RecommendationItem key={index} recommendation={rec} />
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="empty-state">
                <div className="empty-icon">📝</div>
                <div className="empty-text">请先构建正则表达式</div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'optimize' && (
          <div className="optimization-section">
            <div className="section-header">
              <span className="section-icon">💡</span>
              <span className="section-title">表达式优化</span>
              {optimizationResult.canOptimize && (
                <button
                  className="btn btn-sm btn-success"
                  onClick={handleApplyAllOptimizations}
                >
                  应用全部优化
                </button>
              )}
            </div>

            {pattern ? (
              <>
                {optimizationResult.canOptimize ? (
                  <div className="optimizations-list">
                    {optimizationResult.optimizations.map((opt, index) => (
                      <OptimizationItem
                        key={index}
                        optimization={opt}
                        onApply={() => handleApplyOptimization(opt)}
                      />
                    ))}
                  </div>
                ) : (
                  <div className="empty-state">
                    <div className="empty-icon">✨</div>
                    <div className="empty-text">表达式已经很优化了！</div>
                    <div className="empty-desc">没有找到可优化的地方</div>
                  </div>
                )}

                {optimizationResult.canOptimize && (
                  <div className="optimized-preview">
                    <div className="preview-label">优化后的表达式：</div>
                    <code className="preview-code">{optimizationResult.optimizedPattern}</code>
                  </div>
                )}
              </>
            ) : (
              <div className="empty-state">
                <div className="empty-icon">📝</div>
                <div className="empty-text">请先构建正则表达式</div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'password' && (
          <PasswordStrengthChecker />
        )}
      </div>
    </div>
  );
};

export default RegexOptimizer;
