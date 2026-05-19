import React, { useState, useCallback, useEffect } from 'react';
import LezerCodeSnippet from './components/LezerCodeSnippet';
import { runBenchmark, printBenchmarkTable, generateSummary } from './utils/benchmark';
import { LezerParser } from './lezer/parser';
import type { BenchmarkResult } from './utils/benchmark';

const sampleCode = `// Lezer Parser 语法高亮示例
class CodeHighlighter {
  private parser: LezerParser;
  
  constructor(language: string) {
    this.parser = new LezerParser(language);
  }

  highlight(code: string): string[] {
    const result = this.parser.parse(code);
    const highlighter = new SyntaxHighlighter(result.tree, code);
    return highlighter.renderToLines();
  }

  getSyntaxTree() {
    return this.parser.getSyntaxTree();
  }
}

// 定义接口
interface HighlightResult {
  lines: string[];
  duration: number;
  nodeCount: number;
}

// 使用示例
const highlighter = new CodeHighlighter('javascript');

const code = 'function hello() { return "world"; }';
const result = highlighter.highlight(code);
console.log('Highlighted lines:', result.length);

// 处理异常
try {
  highlighter.highlight('invalid code!');
} catch (error) {
  console.error('Highlighting failed:', error);
}

// 导出默认值
export default CodeHighlighter;
`;

function App() {
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');
  const [showLineNumbers, setShowLineNumbers] = useState(true);
  const [enableFolding, setEnableFolding] = useState(true);
  const [showMinimap, setShowMinimap] = useState(false);
  const [enableLSP, setEnableLSP] = useState(false);
  const [benchmarkResults, setBenchmarkResults] = useState<BenchmarkResult[]>([]);
  const [isBenchmarking, setIsBenchmarking] = useState(false);
  const [benchmarkSummary, setBenchmarkSummary] = useState<string>('');

  const handleRunBenchmark = useCallback(async () => {
    setIsBenchmarking(true);
    try {
      const results = await runBenchmark({ iterations: 3, warmup: true });
      setBenchmarkResults(results);
      setBenchmarkSummary(printBenchmarkTable(results));
      const summary = generateSummary(results);
      console.log('Average improvement:', summary.averageImprovement.toFixed(1) + '%');
    } catch (error) {
      console.error('Benchmark failed:', error);
    } finally {
      setIsBenchmarking(false);
    }
  }, []);

  return (
    <div className="app-container" style={{ minHeight: '100vh', background: theme === 'dark' ? '#1a1a2e' : '#f5f5f5', padding: '24px', transition: 'background 0.3s ease' }}>
      <div className="app-header" style={{ textAlign: 'center', marginBottom: '32px' }}>
        <h1 style={{ 
      fontSize: '2.5rem', 
      fontWeight: 700,
      marginBottom: '8px',
      color: theme === 'dark' ? '#fff' : '#1a1a2e'
      }}>
        🔬 Lezer 代码高亮组件
        </h1>
        <p style={{ 
      fontSize: '1.1rem', 
      color: theme === 'dark' ? '#a0a0a0' : '#666'
      }}>
          基于 LR 解析器的高性能语法高亮系统
        </p>
      </div>

      <div className="control-panel" style={{
        background: theme === 'dark' ? '#16213e' : '#fff',
        borderRadius: '12px',
        padding: '20px 24px',
        marginBottom: '24px',
        boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
      }}>
        <h2 style={{ 
      fontSize: '1.25rem', 
      fontWeight: 600,
      marginBottom: '16px',
      color: theme === 'dark' ? '#e94560' : '#1a1a2e'
      }}>
          ⚙️ 配置选项
        </h2>
        <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={showLineNumbers}
              onChange={(e) => setShowLineNumbers(e.target.checked)}
              style={{ width: '18px', height: '18px', accentColor: '#e94560' }}
            />
            <span style={{ color: theme === 'dark' ? '#e0e0e0' : '#333' }}>显示行号</span>
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={enableFolding}
              onChange={(e) => setEnableFolding(e.target.checked)}
              style={{ width: '18px', height: '18px', accentColor: '#e94560' }}
            />
            <span style={{ color: theme === 'dark' ? '#e0e0e0' : '#333' }}>代码折叠</span>
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={showMinimap}
              onChange={(e) => setShowMinimap(e.target.checked)}
              style={{ width: '18px', height: '18px', accentColor: '#e94560' }}
            />
            <span style={{ color: theme === 'dark' ? '#e0e0e0' : '#333' }}>代码缩略图</span>
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={enableLSP}
              onChange={(e) => setEnableLSP(e.target.checked)}
              style={{ width: '18px', height: '18px', accentColor: '#e94560' }}
            />
            <span style={{ color: theme === 'dark' ? '#e0e0e0' : '#333' }}>LSP 功能</span>
          </label>
          <button
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            style={{
              padding: '8px 16px',
              borderRadius: '8px',
              border: 'none',
              background: theme === 'dark' ? '#e94560' : '#1a1a2e',
              color: '#fff',
              cursor: 'pointer',
              fontWeight: 500,
              transition: 'transform 0.2s ease',
            }}
            onMouseOver={(e) => { e.currentTarget.style.transform = 'scale(1.05)'; }}
            onMouseOut={(e) => { e.currentTarget.style.transform = 'scale(1)'; }}
          >
            {theme === 'dark' ? '☀️ 亮色主题' : '🌙 暗色主题'}
          </button>
        </div>
      </div>

      <div className="main-content" style={{ maxWidth: '1200px', margin: '0 auto' }}>
        <div className="code-demo" style={{ marginBottom: '32px' }}>
          <h2 style={{ 
      fontSize: '1.5rem', 
      fontWeight: 600,
      marginBottom: '16px',
      color: theme === 'dark' ? '#fff' : '#1a1a2e'
      }}>
            📝 代码高亮演示
          </h2>
          <LezerCodeSnippet
            code={sampleCode}
            language="typescript"
            theme={theme}
            showLineNumbers={showLineNumbers}
            enableFolding={enableFolding}
            enableLSP={enableLSP}
            showMinimap={showMinimap}
            height="500px"
          />
        </div>

        <div className="feature-cards" style={{ 
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
      gap: '20px',
      marginBottom: '32px',
      }}>
          {[
            {
              icon: '⚡',
              title: '增量解析',
              desc: '使用 Lezer LR 解析器，支持增量语法树复用，性能提升显著',
              color: '#00d9ff',
            },
            {
              icon: '🔍',
              title: '语法树 API',
              desc: '完整的语法树遍历接口，支持节点查询、查找定义等高级操作',
              color: '#0f0',
            },
            {
              icon: '📊',
              title: 'LSP 协议',
              desc: '内置代码补全、定义跳转、引用查找等编辑器级功能',
              color: '#ff6b6b',
            },
            {
              icon: '🎯',
              title: '代码折叠',
              desc: '自动识别函数、类、条件语句等可折叠区域',
              color: '#ffd93d',
            },
            {
              icon: '🗺️',
              title: '代码缩略图',
              desc: '右侧代码地图，快速定位长代码',
              color: '#c084fc',
            },
            {
              icon: '🔒',
              title: '安全可靠',
              desc: '无正则回溯问题，避免 ReDoS 攻击风险',
              color: '#34d399',
            },
          ].map((feature, index) => (
            <div
              key={index}
              style={{
                background: theme === 'dark' ? '#16213e' : '#fff',
                borderRadius: '12px',
                padding: '20px',
                boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
                transition: 'transform 0.2s ease, box-shadow 0.2s ease',
              }}
              onMouseOver={(e) => {
                e.currentTarget.style.transform = 'translateY(-4px)';
                e.currentTarget.style.boxShadow = '0 8px 24px rgba(0,0,0,0.15)';
              }}
              onMouseOut={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.1)';
              }}
            >
              <div style={{ fontSize: '2.5rem', marginBottom: '12px' }}>
                {feature.icon}
              </div>
              <h3 style={{ 
                fontSize: '1.1rem',
                fontWeight: 600,
                marginBottom: '8px',
                color: feature.color,
              }}>
                {feature.title}
              </h3>
              <p style={{ 
                fontSize: '0.95rem',
                color: theme === 'dark' ? '#a0a0a0' : '#666',
                lineHeight: 1.6,
              }}>
                {feature.desc}
              </p>
            </div>
          ))}
        </div>

        <div className="benchmark-section" style={{
          background: theme === 'dark' ? '#16213e' : '#fff',
          borderRadius: '12px',
          padding: '24px',
          boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <h2 style={{ 
      fontSize: '1.5rem', 
      fontWeight: 600,
      color: theme === 'dark' ? '#fff' : '#1a1a2e'
      }}>
              📈 性能基准测试
            </h2>
            <button
              onClick={handleRunBenchmark}
              disabled={isBenchmarking}
              style={{
                padding: '10px 20px',
                borderRadius: '8px',
                border: 'none',
                background: isBenchmarking ? '#666' : '#e94560',
                color: '#fff',
                cursor: isBenchmarking ? 'not-allowed' : 'pointer',
                fontWeight: 600,
                fontSize: '1rem',
                transition: 'all 0.2s ease',
              }}
            >
              {isBenchmarking ? '⏳ 测试中...' : '🚀 运行测试'}
            </button>
          </div>

          {benchmarkSummary && (
            <div style={{
              background: theme === 'dark' ? '#0f0f23' : '#f8f9fa',
              borderRadius: '8px',
              padding: '16px',
              overflowX: 'auto',
            }}>
              <pre style={{
                fontFamily: "'Fira Code', 'Consolas', monospace",
                fontSize: '14px',
                color: theme === 'dark' ? '#0f0' : '#006400',
                margin: 0,
                whiteSpace: 'pre-wrap',
              }}>
                {benchmarkSummary}
              </pre>
            </div>
          )}

          {benchmarkResults.length > 0 && (
            <div style={{ marginTop: '20px', padding: '16px', background: theme === 'dark' ? 'rgba(233, 69, 96, 0.1)' : 'rgba(233, 69, 96, 0.05)', borderRadius: '8px' }}>
              <p style={{ 
                color: theme === 'dark' ? '#ff6b6b' : '#e94560',
                fontWeight: 600,
                fontSize: '1.1rem',
                margin: 0,
              }}>
                🎯 平均性能提升: {generateSummary(benchmarkResults).averageImprovement.toFixed(1)}%
              </p>
            </div>
          )}
        </div>

        <div className="architecture-section" style={{
          marginTop: '32px',
          background: theme === 'dark' ? '#16213e' : '#fff',
          borderRadius: '12px',
          padding: '24px',
          boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
        }}>
          <h2 style={{ 
      fontSize: '1.5rem', 
      fontWeight: 600,
      marginBottom: '20px',
      color: theme === 'dark' ? '#fff' : '#1a1a2e'
      }}>
            🏗️ 架构对比
          </h2>
          <div style={{ 
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: '24px',
          }}>
            <div>
              <h3 style={{ 
                color: '#c678dd',
                fontSize: '1.1rem',
                marginBottom: '12px',
                fontWeight: 600,
              }}>
                ❌ Prism.js (旧方案)
              </h3>
              <ul style={{
                listStyle: 'none',
                padding: 0,
                margin: 0,
              }}>
                {[
                  '正则回溯导致 ReDoS 安全风险',
                  '语法规则难以维护和扩展',
                  '大文件解析性能线性下降',
                  '无语法树，无法支持 LSP 功能',
                  '错误恢复能力差',
                ].map((item, i) => (
                  <li key={i} style={{
                    padding: '8px 0',
                    paddingLeft: '28px',
                    position: 'relative',
                    color: theme === 'dark' ? '#ff6b6b' : '#dc2626',
                  }}>
                    <span style={{ position: 'absolute', left: 0, color: '#ff4444' }}>✗</span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h3 style={{ 
                color: '#4ade80',
                fontSize: '1.1rem',
                marginBottom: '12px',
                fontWeight: 600,
              }}>
                ✓ Lezer (新方案)
              </h3>
              <ul style={{
                listStyle: 'none',
                padding: 0,
                margin: 0,
              }}>
                {[
                  'LR 解析器，无正则回溯问题',
                  '语法定义清晰，易于扩展',
                  '增量解析，复用已有语法树',
                  '完整语法树，支持 LSP 级功能',
                  '内置错误恢复机制',
                ].map((item, i) => (
                  <li key={i} style={{
                    padding: '8px 0',
                    paddingLeft: '28px',
                    position: 'relative',
                    color: theme === 'dark' ? '#4ade80' : '#16a34a',
                  }}>
                    <span style={{ position: 'absolute', left: 0, color: '#22c55e' }}>✓</span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>

        <div className="api-section" style={{
          marginTop: '32px',
          background: theme === 'dark' ? '#16213e' : '#fff',
          borderRadius: '12px',
          padding: '24px',
          boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
        }}>
          <h2 style={{ 
      fontSize: '1.5rem', 
      fontWeight: 600,
      marginBottom: '20px',
      color: theme === 'dark' ? '#fff' : '#1a1a2e'
      }}>
            📚 API 接口
          </h2>
          <LezerCodeSnippet
            code={`// LezerParser - 高性能代码高亮组件 API
import LezerCodeSnippet 组件 Props

interface LezerCodeSnippetProps {
  code: string;                    // 要高亮的代码
  language: Language;               // 编程语言
  showLineNumbers?: boolean;      // 是否显示行号
  theme?: 'dark' | 'light';    // 主题
  enableFolding?: boolean;         // 启用代码折叠
  enableLSP?: boolean;           // 启用 LSP 功能
  showMinimap?: boolean;       // 显示代码缩略图
  height?: string | number;     // 组件高度
  width?: string | number;      // 组件宽度
}

// 使用示例
<LezerCodeSnippet
  code={code}
  language="typescript"
  theme="dark"
  enableFolding={true}
  showMinimap={true}
  height="500px"
/>

// 性能基准测试
await runBenchmark({
  iterations: 5,
  warmup: true,
});
`}
            language="typescript"
            theme={theme}
            showLineNumbers={true}
            enableFolding={true}
          />
        </div>
      </div>

      <div className="footer" style={{
        textAlign: 'center',
        marginTop: '48px',
        padding: '24px',
        color: theme === 'dark' ? '#666' : '#888',
        fontSize: '0.9rem',
      }}>
        <p>基于 Lezer Parser + React + TypeScript 构建</p>
        <p style={{ marginTop: '8px', fontSize: '0.85rem' }}>
          LR 解析器 · 增量解析 · 语法树 API · LSP 协议支持
        </p>
      </div>
    </div>
  );
}

export default App;
