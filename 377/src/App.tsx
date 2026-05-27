import { useEffect, useMemo, useRef, useState } from 'react';
import { parse, ParseContext } from './engine/parser';
import { evaluate, UserFunction } from './engine/evaluator';
import {
  upsertHistory,
  clearHistory,
  deleteHistory,
  getAllHistory,
  HistoryItem,
} from './store/HistoryStore';
import {
  addUserFunction,
  deleteUserFunction,
  getAllUserFunctions,
  updateUserFunction,
  UserFunctionDef,
} from './store/UserFunctionStore';
import FunctionEditor from './components/FunctionEditor';
import GraphCanvas from './components/GraphCanvas';
import UnitConverter from './components/UnitConverter';
import './App.css';

type AngleMode = 'deg' | 'rad';
type Tab = 'calc' | 'graph' | 'unit' | 'functions';

interface ButtonDef {
  label: string;
  value?: string;
  kind?: 'num' | 'op' | 'fn' | 'ctrl' | 'eq';
  action?: 'clear' | 'backspace' | 'equals' | 'toggleAngle' | 'ans';
  span?: number;
}

const BUTTONS: ButtonDef[][] = [
  [
    { label: 'sin', value: 'sin(', kind: 'fn' },
    { label: 'cos', value: 'cos(', kind: 'fn' },
    { label: 'tan', value: 'tan(', kind: 'fn' },
    { label: 'π', value: 'pi', kind: 'fn' },
  ],
  [
    { label: 'asin', value: 'asin(', kind: 'fn' },
    { label: 'acos', value: 'acos(', kind: 'fn' },
    { label: 'atan', value: 'atan(', kind: 'fn' },
    { label: 'e', value: 'e', kind: 'fn' },
  ],
  [
    { label: 'log', value: 'log(', kind: 'fn' },
    { label: 'ln', value: 'ln(', kind: 'fn' },
    { label: '√', value: 'sqrt(', kind: 'fn' },
    { label: 'x^y', value: '^', kind: 'op' },
  ],
  [
    { label: '(', value: '(', kind: 'op' },
    { label: ')', value: ')', kind: 'op' },
    { label: 'n!', value: '!', kind: 'op' },
    { label: '÷', value: '/', kind: 'op' },
  ],
  [
    { label: '7', value: '7', kind: 'num' },
    { label: '8', value: '8', kind: 'num' },
    { label: '9', value: '9', kind: 'num' },
    { label: '×', value: '*', kind: 'op' },
  ],
  [
    { label: '4', value: '4', kind: 'num' },
    { label: '5', value: '5', kind: 'num' },
    { label: '6', value: '6', kind: 'num' },
    { label: '−', value: '-', kind: 'op' },
  ],
  [
    { label: '1', value: '1', kind: 'num' },
    { label: '2', value: '2', kind: 'num' },
    { label: '3', value: '3', kind: 'num' },
    { label: '+', value: '+', kind: 'op' },
  ],
  [
    { label: '0', value: '0', kind: 'num' },
    { label: '.', value: '.', kind: 'num' },
    { label: '⌫', action: 'backspace', kind: 'ctrl' },
    { label: '=', action: 'equals', kind: 'eq' },
  ],
];

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('calc');
  const [expression, setExpression] = useState('');
  const [graphExpression, setGraphExpression] = useState('sin(x)');
  const [xRange, setXRange] = useState<[number, number]>([-10, 10]);
  const [yRange, setYRange] = useState<[number, number]>([-5, 5]);
  const [angleMode, setAngleMode] = useState<AngleMode>('rad');
  const [ans, setAns] = useState<string>('0');
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [userFunctions, setUserFunctions] = useState<UserFunctionDef[]>([]);
  const [showEditor, setShowEditor] = useState(false);
  const [editingFn, setEditingFn] = useState<UserFunctionDef | undefined>();
  const [graphError, setGraphError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getAllHistory().then(setHistory).catch(() => undefined);
    getAllUserFunctions().then(setUserFunctions).catch(() => undefined);
  }, []);

  const parseContext: ParseContext = useMemo(() => ({
    knownFunctions: new Set(userFunctions.map((f) => f.name)),
    allowFreeVariables: false,
  }), [userFunctions]);

  const userFunctionsForEval: UserFunction[] = useMemo(() => (
    userFunctions.map((f) => ({ name: f.name, params: f.params, expression: f.expression }))
  ), [userFunctions]);

  const { result, error } = useMemo(() => {
    if (!expression.trim()) return { result: '', error: null as string | null };
    const { ast, error: parseError } = parse(expression, parseContext);
    if (parseError) {
      return { result: '', error: parseError.message };
    }
    try {
      const value = evaluate(ast!, { angleMode, ans, userFunctions: userFunctionsForEval });
      return { result: value, error: null };
    } catch (e) {
      return { result: '', error: (e as Error).message };
    }
  }, [expression, angleMode, ans, parseContext, userFunctionsForEval]);

  const insert = (text: string) => {
    setExpression((prev) => prev + text);
    inputRef.current?.focus();
  };

  const handleEquals = async () => {
    if (!expression.trim()) return;
    const { ast, error: parseError } = parse(expression, parseContext);
    if (parseError || !ast) return;
    try {
      const value = evaluate(ast, { angleMode, ans, userFunctions: userFunctionsForEval });
      setAns(value);
      const saved = await upsertHistory({ expression, result: value, timestamp: Date.now() });
      setHistory((prev) => {
        const filtered = prev.filter((h) => h.id !== saved.id);
        return [saved, ...filtered];
      });
      setExpression(value);
    } catch {
      /* ignore */
    }
  };

  const handleButton = (btn: ButtonDef) => {
    if (btn.action === 'backspace') {
      setExpression((prev) => prev.slice(0, -1));
      return;
    }
    if (btn.action === 'equals') {
      handleEquals();
      return;
    }
    if (btn.action === 'toggleAngle') {
      setAngleMode((m) => (m === 'deg' ? 'rad' : 'deg'));
      return;
    }
    if (btn.action === 'ans') {
      insert('ans');
      return;
    }
    if (btn.value) insert(btn.value);
  };

  const handleKey = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleEquals();
    }
  };

  const handleClear = () => {
    setExpression('');
  };

  const handleUseHistory = (item: HistoryItem) => {
    setExpression(item.expression);
    setAns(item.result);
    inputRef.current?.focus();
  };

  const handleDeleteHistory = async (id: number) => {
    await deleteHistory(id);
    setHistory((prev) => prev.filter((h) => h.id !== id));
  };

  const handleClearHistory = async () => {
    await clearHistory();
    setHistory([]);
  };

  const handleSaveFunction = async (fn: Omit<UserFunctionDef, 'id' | 'timestamp'>) => {
    try {
      if (editingFn && editingFn.id !== undefined) {
        const updated = await updateUserFunction(editingFn.id, fn);
        setUserFunctions((prev) => prev.map((f) => (f.id === updated.id ? updated : f)));
      } else {
        const created = await addUserFunction(fn);
        setUserFunctions((prev) => [created, ...prev]);
      }
    } catch (e) {
      alert((e as Error).message);
    }
  };

  const handleDeleteFunction = async (id: number) => {
    if (!confirm('确定删除此函数？')) return;
    await deleteUserFunction(id);
    setUserFunctions((prev) => prev.filter((f) => f.id !== id));
  };

  const handleEditFunction = (fn: UserFunctionDef) => {
    setEditingFn(fn);
    setShowEditor(true);
  };

  const insertFunctionCall = (fn: UserFunctionDef) => {
    const call = `${fn.name}(${fn.params.map(() => '').join(', ')})`;
    if (activeTab === 'calc') {
      setExpression((prev) => prev + call);
      inputRef.current?.focus();
    } else if (activeTab === 'graph') {
      setGraphExpression((prev) => prev + call);
    }
  };

  return (
    <div className="app">
      <div className="main-container">
        <header className="app-header">
          <h1 className="brand">AURORA<span>·</span>Calc</h1>
          <div className="tabs">
            <button
              className={`tab ${activeTab === 'calc' ? 'active' : ''}`}
              onClick={() => setActiveTab('calc')}
              type="button"
            >
              计算器
            </button>
            <button
              className={`tab ${activeTab === 'graph' ? 'active' : ''}`}
              onClick={() => setActiveTab('graph')}
              type="button"
            >
              绘图
            </button>
            <button
              className={`tab ${activeTab === 'unit' ? 'active' : ''}`}
              onClick={() => setActiveTab('unit')}
              type="button"
            >
              单位转换
            </button>
            <button
              className={`tab ${activeTab === 'functions' ? 'active' : ''}`}
              onClick={() => setActiveTab('functions')}
              type="button"
            >
              函数
            </button>
          </div>
        </header>

        {activeTab === 'calc' && (
          <div className="tab-content">
            <div className="calculator">
              <header className="calc-header">
                <div className="header-controls">
                  <button
                    className={`mode-switch ${angleMode === 'deg' ? 'active' : ''}`}
                    onClick={() => setAngleMode('deg')}
                    type="button"
                  >
                    DEG
                  </button>
                  <button
                    className={`mode-switch ${angleMode === 'rad' ? 'active' : ''}`}
                    onClick={() => setAngleMode('rad')}
                    type="button"
                  >
                    RAD
                  </button>
                  <button className="ctrl-btn" onClick={() => insert('ans')} type="button">
                    Ans
                  </button>
                  <button className="ctrl-btn" onClick={handleClear} type="button">
                    AC
                  </button>
                </div>
              </header>

              <div className="display">
                <input
                  ref={inputRef}
                  className="display-input"
                  value={expression}
                  onChange={(e) => setExpression(e.target.value)}
                  onKeyDown={handleKey}
                  placeholder="输入表达式，例如 sin(pi/2) + log(100)"
                  spellCheck={false}
                  autoFocus
                />
                <div className={`display-result ${error ? 'error' : ''}`}>
                  {error ? <span className="error-text">⚠ {error}</span> : result || '0'}
                </div>
              </div>

              <div className="keypad">
                {BUTTONS.map((row, i) => (
                  <div className="keypad-row" key={i}>
                    {row.map((btn, j) => (
                      <button
                        key={j}
                        className={`key key-${btn.kind || 'num'}`}
                        onClick={() => handleButton(btn)}
                        type="button"
                      >
                        {btn.label}
                      </button>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'graph' && (
          <div className="tab-content">
            <div className="graph-panel">
              <div className="graph-header">
                <h2>函数图像</h2>
              </div>
              <div className="graph-input-row">
                <input
                  className="form-input graph-input"
                  value={graphExpression}
                  onChange={(e) => setGraphExpression(e.target.value)}
                  placeholder="y = f(x)，例如 sin(x) + cos(2*x)"
                  spellCheck={false}
                />
                <div className="range-inputs">
                  <div className="range-group">
                    <label>X:</label>
                    <input
                      className="range-input"
                      type="number"
                      value={xRange[0]}
                      onChange={(e) => setXRange([parseFloat(e.target.value) || -10, xRange[1]])}
                    />
                    <span>~</span>
                    <input
                      className="range-input"
                      type="number"
                      value={xRange[1]}
                      onChange={(e) => setXRange([xRange[0], parseFloat(e.target.value) || 10])}
                    />
                  </div>
                  <div className="range-group">
                    <label>Y:</label>
                    <input
                      className="range-input"
                      type="number"
                      value={yRange[0]}
                      onChange={(e) => setYRange([parseFloat(e.target.value) || -5, yRange[1]])}
                    />
                    <span>~</span>
                    <input
                      className="range-input"
                      type="number"
                      value={yRange[1]}
                      onChange={(e) => setYRange([yRange[0], parseFloat(e.target.value) || 5])}
                    />
                  </div>
                </div>
              </div>
              {graphError && <div className="form-error">{graphError}</div>}
              <div className="graph-wrapper">
                <GraphCanvas
                  expression={graphExpression}
                  xRange={xRange}
                  yRange={yRange}
                  width={760}
                  height={420}
                  userFunctions={userFunctionsForEval}
                  angleMode={angleMode}
                  errorCallback={setGraphError}
                />
              </div>
            </div>
          </div>
        )}

        {activeTab === 'unit' && (
          <div className="tab-content">
            <div className="unit-panel">
              <UnitConverter />
            </div>
          </div>
        )}

        {activeTab === 'functions' && (
          <div className="tab-content">
            <div className="functions-panel">
              <div className="panel-header">
                <h2>自定义函数</h2>
                <button
                  className="btn btn-primary"
                  onClick={() => { setEditingFn(undefined); setShowEditor(true); }}
                  type="button"
                >
                  + 新建函数
                </button>
              </div>
              {userFunctions.length === 0 ? (
                <div className="history-empty">
                  暂无自定义函数。点击"新建函数"创建，例如：quad(a, b, c, x) = a*x^2 + b*x + c
                </div>
              ) : (
                <div className="function-list">
                  {userFunctions.map((fn) => (
                    <div className="function-item" key={fn.id}>
                      <div className="function-info">
                        <div className="function-signature">
                          <span className="function-name">{fn.name}</span>
                          <span className="function-params">
                            ({fn.params.join(', ')})
                          </span>
                          <span className="function-eq"> = </span>
                          <span className="function-expr">{fn.expression}</span>
                        </div>
                      </div>
                      <div className="function-actions">
                        <button
                          className="ctrl-btn"
                          onClick={() => insertFunctionCall(fn)}
                          type="button"
                          title="插入表达式"
                        >
                          插入
                        </button>
                        <button
                          className="ctrl-btn"
                          onClick={() => handleEditFunction(fn)}
                          type="button"
                        >
                          编辑
                        </button>
                        <button
                          className="ctrl-btn danger"
                          onClick={() => fn.id !== undefined && handleDeleteFunction(fn.id)}
                          type="button"
                        >
                          删除
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      <aside className="history">
        <div className="history-header">
          <h2>历史记录</h2>
          {history.length > 0 && (
            <button className="clear-all" onClick={handleClearHistory} type="button">
              全部清空
            </button>
          )}
        </div>
        <div className="history-list">
          {history.length === 0 ? (
            <div className="history-empty">暂无记录</div>
          ) : (
            history.map((item) => (
              <div
                className="history-item"
                key={item.id}
                onClick={() => handleUseHistory(item)}
              >
                <div className="history-expr">{item.expression}</div>
                <div className="history-result">= {item.result}</div>
                <button
                  className="history-delete"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (item.id !== undefined) handleDeleteHistory(item.id);
                  }}
                  type="button"
                >
                  ×
                </button>
              </div>
            ))
          )}
        </div>
      </aside>

      {showEditor && (
        <FunctionEditor
          onClose={() => { setShowEditor(false); setEditingFn(undefined); }}
          onSave={handleSaveFunction}
          existing={editingFn}
          existingNames={userFunctions
            .filter((f) => f.id !== editingFn?.id)
            .map((f) => f.name)}
        />
      )}
    </div>
  );
}

export default App;
