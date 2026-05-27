import { useState } from 'react';
import { parse, getAllBuiltinFunctions } from '../engine/parser';
import { UserFunction } from '../engine/evaluator';
import { UserFunctionDef } from '../store/UserFunctionStore';

interface FunctionEditorProps {
  onClose: () => void;
  onSave: (fn: Omit<UserFunctionDef, 'id' | 'timestamp'>) => void;
  existing?: UserFunctionDef;
  existingNames: string[];
}

export default function FunctionEditor({ onClose, onSave, existing, existingNames }: FunctionEditorProps) {
  const [name, setName] = useState(existing?.name ?? '');
  const [params, setParams] = useState(existing?.params.join(', ') ?? '');
  const [expression, setExpression] = useState(existing?.expression ?? '');
  const [error, setError] = useState<string | null>(null);

  const builtin = getAllBuiltinFunctions();
  const reserved = new Set([...builtin, 'pi', 'e', 'ans', 'x']);

  const validate = (): boolean => {
    if (!name.trim()) {
      setError('请输入函数名');
      return false;
    }
    if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(name.trim())) {
      setError('函数名只能包含字母、数字和下划线，且不能以数字开头');
      return false;
    }
    if (reserved.has(name.trim().toLowerCase())) {
      setError(`函数名 '${name.trim()}' 已被内置函数占用`);
      return false;
    }
    if (!existing && existingNames.includes(name.trim().toLowerCase())) {
      setError(`函数名 '${name.trim()}' 已存在`);
      return false;
    }
    const paramList = params
      .split(',')
      .map((p) => p.trim())
      .filter((p) => p);
    if (paramList.length === 0) {
      setError('至少需要一个参数');
      return false;
    }
    for (const p of paramList) {
      if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(p)) {
        setError(`参数名 '${p}' 格式无效`);
        return false;
      }
      if (reserved.has(p.toLowerCase()) || paramList.filter((x) => x.toLowerCase() === p.toLowerCase()).length > 1) {
        setError(`参数名 '${p}' 无效或重复`);
        return false;
      }
    }
    if (!expression.trim()) {
      setError('请输入函数表达式');
      return false;
    }
    const knownIdents = new Set([...paramList, 'pi', 'e', 'ans']);
    const { error: parseError } = parse(expression, {
      knownIdentifiers: knownIdents,
      allowFreeVariables: false,
    });
    if (parseError) {
      setError(`表达式错误: ${parseError.message}`);
      return false;
    }
    setError(null);
    return true;
  };

  const handleSave = () => {
    if (!validate()) return;
    const paramList = params
      .split(',')
      .map((p) => p.trim())
      .filter((p) => p);
    onSave({ name: name.trim().toLowerCase(), params: paramList, expression: expression.trim() });
    onClose();
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{existing ? '编辑函数' : '新建函数'}</h2>
          <button className="modal-close" onClick={onClose} type="button">×</button>
        </div>
        <div className="modal-body">
          <div className="form-field">
            <label>函数名</label>
            <input
              className="form-input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="例如: quad"
              spellCheck={false}
            />
          </div>
          <div className="form-field">
            <label>参数列表（逗号分隔）</label>
            <input
              className="form-input"
              value={params}
              onChange={(e) => setParams(e.target.value)}
              placeholder="例如: a, b, c, x"
              spellCheck={false}
            />
          </div>
          <div className="form-field">
            <label>表达式</label>
            <input
              className="form-input"
              value={expression}
              onChange={(e) => setExpression(e.target.value)}
              placeholder="例如: a*x^2 + b*x + c"
              spellCheck={false}
            />
          </div>
          {error && <div className="form-error">{error}</div>}
          <div className="form-preview">
            预览: <code>{name.trim() || 'f'}({params || 'x'}) = {expression || '...'}</code>
          </div>
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose} type="button">取消</button>
          <button className="btn btn-primary" onClick={handleSave} type="button">保存</button>
        </div>
      </div>
    </div>
  );
}
