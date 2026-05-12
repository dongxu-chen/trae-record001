import Editor, { loader } from '@monaco-editor/react';
import { useCallback } from 'react';

loader.config({
  paths: {
    vs: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.41.0/min/vs',
  },
});

function CodeEditor({ code, onChange, onRun, language = 'javascript' }) {
  const handleEditorChange = useCallback((value) => {
    if (onChange && typeof value === 'string') {
      onChange(value);
    }
  }, [onChange]);

  const handleEditorMount = useCallback((editor, monaco) => {
    editor.addCommand(
      monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter,
      () => {
        if (onRun) {
          onRun();
        }
      }
    );

    editor.addCommand(
      monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS,
      () => {
        if (onRun) {
          onRun();
        }
      }
    );

    editor.onDidBlurEditorWidget(() => {
      const currentValue = editor.getValue();
      if (onChange) {
        onChange(currentValue);
      }
    });
  }, [onChange, onRun]);

  return (
    <div className="editor-container">
      <Editor
        height="100%"
        language={language}
        value={code}
        onChange={handleEditorChange}
        onMount={handleEditorMount}
        theme="vs-dark"
        options={{
          fontSize: 14,
          fontFamily: 'Fira Code, Consolas, Monaco, monospace',
          minimap: { enabled: false },
          automaticLayout: true,
          scrollBeyondLastLine: false,
          lineNumbers: 'on',
          wordWrap: 'on',
          tabSize: 2,
          detectIndentation: false,
          formatOnPaste: true,
          formatOnType: true,
          folding: true,
          foldingStrategy: 'indentation',
          suggestOnTriggerCharacters: true,
          acceptSuggestionOnCommitCharacter: true,
          acceptSuggestionOnEnter: 'on',
          quickSuggestions: {
            other: true,
            comments: false,
            strings: false,
          },
          parameterHints: {
            enabled: true,
          },
          renderWhitespace: 'selection',
          renderLineHighlight: 'line',
          cursorBlinking: 'smooth',
          cursorSmoothCaretAnimation: 'on',
          smoothScrolling: true,
          padding: {
            top: 10,
            bottom: 10,
          },
        }}
      />
    </div>
  );
}

export default CodeEditor;
