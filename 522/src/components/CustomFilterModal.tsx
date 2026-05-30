import { useState, useRef } from 'react';
import { X, Upload, FileCode, CheckCircle, AlertCircle, Plus, Shield, RotateCcw } from 'lucide-react';
import useFilterStore from '@/store/filterStore';
import { useShader } from '@/contexts/ShaderContext';
import { cn } from '@/lib/utils';

interface CustomFilterModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function CustomFilterModal({
  isOpen,
  onClose,
}: CustomFilterModalProps) {
  const [filterName, setFilterName] = useState('');
  const [shaderCode, setShaderCode] = useState('');
  const [validationResult, setValidationResult] = useState<{
    valid: boolean;
    error?: string;
    lineNumber?: number;
  } | null>(null);
  const [syntaxCheckResult, setSyntaxCheckResult] = useState<{
    valid: boolean;
    error?: string;
    lineNumber?: number;
  } | null>(null);
  const [isCompiling, setIsCompiling] = useState(false);
  const [rollbackSuccess, setRollbackSuccess] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { validateShader, registerCustomFilter } = useShader();
  const { addCustomFilter, setActiveFilter } = useFilterStore();

  if (!isOpen) return null;

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const code = event.target?.result as string;
      setShaderCode(code);
      if (!filterName) {
        setFilterName(file.name.replace(/\.(frag|glsl)$/i, ''));
      }
      setValidationResult(null);
      setSyntaxCheckResult(null);
      setRollbackSuccess(false);
    };
    reader.readAsText(file);
  };

  const handleSyntaxCheck = () => {
    if (!shaderCode.trim()) return;

    const result = validateShader(shaderCode);
    setSyntaxCheckResult(result);
    setValidationResult(null);
  };

  const handleValidate = async () => {
    if (!shaderCode.trim()) return;

    const syntaxResult = validateShader(shaderCode);
    setSyntaxCheckResult(syntaxResult);

    if (!syntaxResult.valid) {
      setValidationResult(null);
      return;
    }

    setIsCompiling(true);
    setValidationResult(null);

    await new Promise((resolve) => setTimeout(resolve, 300));

    const result = registerCustomFilter(shaderCode, []);
    if (result.success) {
      setValidationResult({ valid: true });
    } else {
      setValidationResult({
        valid: false,
        error: result.error || '编译失败',
      });
    }

    setIsCompiling(false);
  };

  const handleRollback = () => {
    setShaderCode('');
    setFilterName('');
    setValidationResult(null);
    setSyntaxCheckResult(null);
    setRollbackSuccess(true);
    setTimeout(() => setRollbackSuccess(false), 2000);
  };

  const handleAddFilter = () => {
    if (!filterName.trim() || !shaderCode.trim() || !validationResult?.valid)
      return;

    const result = registerCustomFilter(shaderCode, []);
    if (result.success && result.filterName) {
      addCustomFilter(filterName.trim(), shaderCode, []);
      setActiveFilter(result.filterName);
      setFilterName('');
      setShaderCode('');
      setValidationResult(null);
      setSyntaxCheckResult(null);
      onClose();
    }
  };

  const handleClose = () => {
    setFilterName('');
    setShaderCode('');
    setValidationResult(null);
    setSyntaxCheckResult(null);
    setRollbackSuccess(false);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={handleClose}
      />
      <div className="relative w-full max-w-2xl glass-panel rounded-2xl overflow-hidden animate-fade-in">
        <div className="flex items-center justify-between p-4 border-b border-surface-border">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-neon-purple/20 flex items-center justify-center">
              <Shield size={20} className="text-neon-purple" />
            </div>
            <div>
              <h3 className="font-display font-semibold text-lg neon-text">
                上传自定义滤镜
              </h3>
              <p className="text-sm text-gray-400">
                沙箱环境 · 语法校验 · 错误回滚
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {rollbackSuccess && (
              <span className="text-xs text-green-400 flex items-center gap-1 animate-fade-in">
                <CheckCircle size={14} />
                已回滚
              </span>
            )}
            <button
              onClick={handleRollback}
              className="p-2 rounded-lg hover:bg-surface-hover transition-colors text-gray-400 hover:text-white"
              title="重置所有内容"
            >
              <RotateCcw size={18} />
            </button>
            <button
              onClick={handleClose}
              className="p-2 rounded-lg hover:bg-surface-hover transition-colors"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        <div className="p-6 space-y-6 max-h-[70vh] overflow-y-auto">
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-300">滤镜名称</label>
            <input
              type="text"
              value={filterName}
              onChange={(e) => setFilterName(e.target.value)}
              placeholder="输入滤镜名称..."
              className="w-full px-4 py-3 bg-surface-card border border-surface-border rounded-lg text-sm focus:outline-none focus:border-neon-cyan/50"
            />
          </div>

          <div
            onClick={() => fileInputRef.current?.click()}
            className="border-2 border-dashed border-surface-border hover:border-neon-cyan/50 rounded-lg p-8 text-center cursor-pointer transition-colors"
          >
            <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-surface-card flex items-center justify-center">
              <FileCode size={24} className="text-gray-400" />
            </div>
            <p className="text-sm font-medium">点击上传 .frag 或 .glsl 文件</p>
            <p className="text-xs text-gray-500 mt-1">或在下方编辑器中粘贴代码</p>
            <input
              ref={fileInputRef}
              type="file"
              accept=".frag,.glsl"
              onChange={handleFileUpload}
              className="hidden"
            />
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium text-gray-300">
                GLSL 片段着色器代码
              </label>
              <div className="flex gap-2">
                <button
                  onClick={handleSyntaxCheck}
                  disabled={!shaderCode.trim()}
                  className="px-3 py-1.5 bg-surface-card rounded-md text-sm font-medium hover:bg-surface-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  <Shield size={14} />
                  语法检查
                </button>
                <button
                  onClick={handleValidate}
                  disabled={isCompiling || !shaderCode.trim()}
                  className="px-3 py-1.5 bg-surface-card rounded-md text-sm font-medium hover:bg-surface-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  <Upload size={14} />
                  {isCompiling ? '编译中...' : '验证编译'}
                </button>
              </div>
            </div>

            <div className="relative">
              <textarea
                value={shaderCode}
                onChange={(e) => {
                  setShaderCode(e.target.value);
                  setValidationResult(null);
                  setSyntaxCheckResult(null);
                }}
                placeholder="粘贴您的 GLSL 片段着色器代码..."
                className="w-full h-64 px-4 py-3 bg-surface-card border border-surface-border rounded-lg text-sm font-mono focus:outline-none focus:border-neon-cyan/50 resize-none"
                spellCheck={false}
              />
              {syntaxCheckResult?.lineNumber && (
                <div className="absolute top-3 right-3 text-xs font-mono text-red-400 bg-red-500/20 px-2 py-1 rounded">
                  第 {syntaxCheckResult.lineNumber} 行
                </div>
              )}
            </div>

            {syntaxCheckResult && !validationResult && (
              <div
                className={cn(
                  'p-3 rounded-lg flex items-start gap-3',
                  syntaxCheckResult.valid
                    ? 'bg-green-500/10 border border-green-500/30'
                    : 'bg-red-500/10 border border-red-500/30'
                )}
              >
                {syntaxCheckResult.valid ? (
                  <CheckCircle size={18} className="text-green-400 mt-0.5" />
                ) : (
                  <AlertCircle size={18} className="text-red-400 mt-0.5" />
                )}
                <div>
                  <p
                    className={cn(
                      'text-sm font-medium',
                      syntaxCheckResult.valid ? 'text-green-400' : 'text-red-400'
                    )}
                  >
                    {syntaxCheckResult.valid
                      ? '语法检查通过！'
                      : '语法检查失败'}
                  </p>
                  {syntaxCheckResult.error && (
                    <p className="text-xs text-gray-400 mt-1">
                      {syntaxCheckResult.error}
                    </p>
                  )}
                </div>
              </div>
            )}

            {validationResult && (
              <div
                className={cn(
                  'p-3 rounded-lg flex items-start gap-3',
                  validationResult.valid
                    ? 'bg-green-500/10 border border-green-500/30'
                    : 'bg-red-500/10 border border-red-500/30'
                )}
              >
                {validationResult.valid ? (
                  <CheckCircle size={18} className="text-green-400 mt-0.5" />
                ) : (
                  <AlertCircle size={18} className="text-red-400 mt-0.5" />
                )}
                <div>
                  <p
                    className={cn(
                      'text-sm font-medium',
                      validationResult.valid ? 'text-green-400' : 'text-red-400'
                    )}
                  >
                    {validationResult.valid
                      ? '着色器编译成功！沙箱验证通过，已自动回滚临时程序。'
                      : '编译失败'}
                  </p>
                  {validationResult.error && (
                    <p className="text-xs text-gray-400 mt-1">
                      {validationResult.error}
                    </p>
                  )}
                  {validationResult.valid && (
                    <p className="text-xs text-gray-500 mt-2 flex items-center gap-1">
                      <Shield size={12} className="text-neon-purple" />
                      安全机制：沙箱编译后已清理临时资源，点击下方"添加滤镜"正式注册
                    </p>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="flex justify-end gap-3 p-4 border-t border-surface-border bg-surface-card/50">
          <button
            onClick={handleClose}
            className="px-4 py-2 bg-surface-card rounded-lg text-sm font-medium hover:bg-surface-hover transition-colors"
          >
            取消
          </button>
          <button
            onClick={handleAddFilter}
            disabled={
              !filterName.trim() || !shaderCode.trim() || !validationResult?.valid
            }
            className="px-6 py-2 bg-gradient-to-r from-neon-cyan to-neon-purple rounded-lg text-sm font-medium text-white hover:shadow-lg hover:shadow-neon-cyan/25 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <Plus size={16} />
            添加滤镜
          </button>
        </div>
      </div>
    </div>
  );
}
