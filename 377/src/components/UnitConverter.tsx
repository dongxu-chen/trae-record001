import { useState } from 'react';
import { UNIT_CATEGORIES, convert, Unit } from '../utils/unitConverter';

export default function UnitConverter() {
  const [categoryId, setCategoryId] = useState(UNIT_CATEGORIES[0].id);
  const [fromId, setFromId] = useState(UNIT_CATEGORIES[0].units[0].id);
  const [toId, setToId] = useState(UNIT_CATEGORIES[0].units[1].id);
  const [value, setValue] = useState<string>('1');
  const [result, setResult] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  const category = UNIT_CATEGORIES.find((c) => c.id === categoryId)!;
  const fromUnit = category.units.find((u) => u.id === fromId)!;
  const toUnit = category.units.find((u) => u.id === toId)!;

  const handleConvert = () => {
    if (!value.trim()) {
      setError('请输入数值');
      setResult('');
      return;
    }
    const num = parseFloat(value);
    if (isNaN(num)) {
      setError('请输入有效的数值');
      setResult('');
      return;
    }
    try {
      const r = convert(num, fromId, toId, categoryId);
      setResult(formatResult(r));
      setError(null);
    } catch (e) {
      setError((e as Error).message);
      setResult('');
    }
  };

  const handleSwap = () => {
    setFromId(toId);
    setToId(fromId);
    setValue(result || value);
    setResult(value);
  };

  const formatResult = (n: number): string => {
    if (Math.abs(n) >= 1e15 || (Math.abs(n) < 1e-6 && n !== 0)) {
      return n.toExponential(10).replace(/\.?0+e/, 'e');
    }
    const s = n.toString();
    if (s.includes('.')) {
      return s.replace(/(\.\d*?)0+$/, '$1').replace(/\.$/, '');
    }
    return s;
  };

  return (
    <div className="unit-converter">
      <div className="converter-header">
        <h2>单位转换</h2>
      </div>

      <div className="category-tabs">
        {UNIT_CATEGORIES.map((cat) => (
          <button
            key={cat.id}
            className={`category-tab ${cat.id === categoryId ? 'active' : ''}`}
            onClick={() => {
              setCategoryId(cat.id);
              setFromId(cat.units[0].id);
              setToId(cat.units[1] ? cat.units[1].id : cat.units[0].id);
              setResult('');
            }}
            type="button"
          >
            {cat.name}
          </button>
        ))}
      </div>

      <div className="converter-body">
        <div className="converter-row">
          <div className="converter-field">
            <label>数值</label>
            <input
              className="form-input"
              type="text"
              value={value}
              onChange={(e) => setValue(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleConvert()}
              spellCheck={false}
              placeholder="输入数值"
            />
          </div>
        </div>

        <div className="converter-row">
          <div className="converter-field">
            <label>源单位</label>
            <select
              className="form-select"
              value={fromId}
              onChange={(e) => { setFromId(e.target.value); setResult(''); }}
            >
              {category.units.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.name} ({u.symbol})
                </option>
              ))}
            </select>
          </div>

          <button className="swap-btn" onClick={handleSwap} type="button" title="交换单位">
            ⇄
          </button>

          <div className="converter-field">
            <label>目标单位</label>
            <select
              className="form-select"
              value={toId}
              onChange={(e) => { setToId(e.target.value); setResult(''); }}
            >
              {category.units.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.name} ({u.symbol})
                </option>
              ))}
            </select>
          </div>
        </div>

        <button className="btn btn-primary convert-btn" onClick={handleConvert} type="button">
          转换
        </button>

        {error && <div className="form-error">{error}</div>}

        {result && (
          <div className="convert-result">
            <div className="result-label">结果</div>
            <div className="result-value">
              {result} <span className="result-unit">{toUnit.symbol}</span>
            </div>
            <div className="result-detail">
              {value} {fromUnit.symbol} = {result} {toUnit.symbol}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
