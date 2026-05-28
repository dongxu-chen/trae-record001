import React, { useMemo, useState, useEffect } from 'react';
import Editor from '@monaco-editor/react';
import { Loader2 } from 'lucide-react';
import { useFlowStore } from '../../store/useFlowStore';
import { generateXStateCode } from '../../generators/xstate';
import { generateSpringStateMachineCode } from '../../generators/spring';
import { generatePlantUMLCode } from '../../generators/plantuml';
import { generateGraphvizCode } from '../../generators/graphviz';
import { generateTestCases, generateJestTests, generatePlainTextTests } from '../../generators/testGenerator';
import { formatTypeScript, formatJavaSimple } from '../../utils/format';
import { CodeFormat } from '../../types';

const formatConfig: Record<CodeFormat, { label: string; language: string; tabSize: number }> = {
  xstate: { label: 'XState', language: 'typescript', tabSize: 2 },
  spring: { label: 'Spring', language: 'java', tabSize: 4 },
  plantuml: { label: 'PlantUML', language: 'plaintext', tabSize: 2 },
  graphviz: { label: 'Graphviz', language: 'plaintext', tabSize: 2 },
  'test-jest': { label: 'Jest', language: 'typescript', tabSize: 2 },
  'test-plain': { label: 'Test Cases', language: 'markdown', tabSize: 2 },
};

export const CodeEditor: React.FC = () => {
  const { nodes, edges, codeFormat, setCodeFormat } = useFlowStore();
  const [formattedCode, setFormattedCode] = useState<string>('');
  const [isFormatting, setIsFormatting] = useState(false);

  const rawCode = useMemo(() => {
    switch (codeFormat) {
      case 'xstate':
        return generateXStateCode(nodes, edges);
      case 'spring':
        return generateSpringStateMachineCode(nodes, edges);
      case 'plantuml':
        return generatePlantUMLCode(nodes, edges);
      case 'graphviz':
        return generateGraphvizCode(nodes, edges);
      case 'test-jest': {
        const testSuite = generateTestCases(nodes, edges);
        return generateJestTests(testSuite);
      }
      case 'test-plain': {
        const testSuite = generateTestCases(nodes, edges);
        return generatePlainTextTests(testSuite);
      }
      default:
        return '';
    }
  }, [nodes, edges, codeFormat]);

  useEffect(() => {
    const formatCode = async () => {
      setIsFormatting(true);
      try {
        let formatted = rawCode;
        if (codeFormat === 'xstate' || codeFormat === 'test-jest') {
          formatted = await formatTypeScript(rawCode);
        } else if (codeFormat === 'spring') {
          formatted = formatJavaSimple(rawCode);
        }
        setFormattedCode(formatted);
      } catch (error) {
        console.error('Formatting error:', error);
        setFormattedCode(rawCode);
      } finally {
        setIsFormatting(false);
      }
    };
    formatCode();
  }, [rawCode, codeFormat]);

  const config = formatConfig[codeFormat];

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between px-4 py-2 border-b border-slate-700/50 bg-slate-800/50">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-slate-400">生成代码</span>
          {isFormatting && (
            <div className="flex items-center gap-1 text-xs text-cyan-400">
              <Loader2 size={12} className="animate-spin" />
              格式化中...
            </div>
          )}
        </div>
        <div className="flex items-center gap-1 flex-wrap">
          {(Object.keys(formatConfig) as CodeFormat[]).map((format) => (
            <button
              key={format}
              onClick={() => setCodeFormat(format)}
              className={`px-2 py-1 text-xs font-medium rounded-md transition-colors ${
                codeFormat === format
                  ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/50'
              }`}
            >
              {formatConfig[format].label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 min-h-0">
        <Editor
          height="100%"
          language={config.language}
          value={formattedCode}
          theme="vs-dark"
          loading={<div className="flex items-center justify-center h-full text-slate-500">加载编辑器...</div>}
          options={{
            minimap: { enabled: false },
            fontSize: 12,
            fontFamily: 'JetBrains Mono, Fira Code, monospace',
            readOnly: true,
            lineNumbers: 'on',
            scrollBeyondLastLine: false,
            automaticLayout: true,
            tabSize: config.tabSize,
            wordWrap: 'on',
            padding: { top: 12, bottom: 12 },
            formatOnPaste: true,
            formatOnType: true,
            smoothScrolling: true,
            cursorBlinking: 'smooth',
          }}
        />
      </div>
    </div>
  );
};
