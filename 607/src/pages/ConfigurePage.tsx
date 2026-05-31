import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, ArrowRight, Play, Target, TrendingUp, Layers, Clock, AlertCircle, CheckCircle2, Sparkles, Info } from 'lucide-react';
import { useDataStore } from '../store/useDataStore';
import { analyzePSM, analyzeDID, lassoSelect } from '../services/api';
import type { AnalysisMethod } from '../../shared/types';

type LassoMethod = 'double_lasso' | 'treatment' | 'outcome' | 'perturbation';

export default function ConfigurePage() {
  const navigate = useNavigate();
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [useAutoSelection, setUseAutoSelection] = useState(false);
  const [lassoMethod, setLassoMethod] = useState<LassoMethod>('double_lasso');
  const [isAutoSelecting, setIsAutoSelecting] = useState(false);
  
  const {
    data,
    columns,
    columnInfo,
    treatment,
    outcome,
    covariates,
    method,
    timeVariable,
    setTreatment,
    setOutcome,
    setCovariates,
    setMethod,
    setTimeVariable,
    setResult,
    setIsLoading,
    setError,
  } = useDataStore();

  const binaryColumns = columnInfo.filter(c => c.type === 'binary').map(c => c.name);
  const numericColumns = columnInfo.filter(c => c.type === 'numeric' || c.type === 'binary').map(c => c.name);
  const availableCovariates = columns.filter(c => c !== treatment && c !== outcome && c !== timeVariable);

  const toggleCovariate = (col: string) => {
    if (covariates.includes(col)) {
      setCovariates(covariates.filter(c => c !== col));
    } else {
      setCovariates([...covariates, col]);
    }
  };

  const selectAllCovariates = () => {
    setCovariates(availableCovariates);
  };

  const clearAllCovariates = () => {
    setCovariates([]);
  };

  const handleAutoSelect = async () => {
    if (!treatment || !outcome || availableCovariates.length === 0) return;
    
    setIsAutoSelecting(true);
    try {
      const result = await lassoSelect(data, treatment, outcome, availableCovariates, lassoMethod);
      setCovariates(result.selected_covariates);
    } catch (err) {
      console.error('Auto selection failed:', err);
    } finally {
      setIsAutoSelecting(false);
    }
  };

  const canRunAnalysis = treatment && outcome && (method === 'psm' || (method === 'did' && timeVariable));

  const handleRunAnalysis = async () => {
    if (!treatment || !outcome) return;
    
    setIsAnalyzing(true);
    setIsLoading(true);
    setError(null);

    try {
      let result;
      if (method === 'psm') {
        result = await analyzePSM(data, treatment, outcome, covariates, useAutoSelection, lassoMethod);
      } else {
        result = await analyzeDID(data, treatment, outcome, covariates, timeVariable || undefined, useAutoSelection, lassoMethod);
      }
      
      setResult(result);
      navigate('/results');
    } catch (err) {
      setError(err instanceof Error ? err.message : '分析失败');
    } finally {
      setIsAnalyzing(false);
      setIsLoading(false);
    }
  };

  if (data.length === 0) {
    return (
      <div className="min-h-screen bg-grid-pattern">
        <div className="container mx-auto px-4 py-8">
          <div className="max-w-2xl mx-auto text-center">
            <div className="card">
              <AlertCircle className="w-12 h-12 text-amber-500 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-gray-800 mb-2">请先上传数据</h3>
              <p className="text-gray-600 mb-4">在配置变量之前，请先上传您的观测数据</p>
              <button onClick={() => navigate('/')} className="btn-primary">
                前往上传数据
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const lassoMethodOptions = [
    { value: 'double_lasso', label: '双重LASSO', desc: '同时预测处理和结果，选择并集' },
    { value: 'treatment', label: '处理预测', desc: '基于处理变量预测选择变量' },
    { value: 'outcome', label: '结果预测', desc: '基于结果变量预测选择变量' },
    { value: 'perturbation', label: '扰动稳定', desc: '多次抽样选择稳定的变量' },
  ];

  return (
    <div className="min-h-screen bg-grid-pattern">
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-5xl mx-auto">
          <div className="flex items-center justify-between mb-8">
            <div>
              <h2 className="font-display text-3xl font-semibold text-primary-800 mb-2">
                配置分析变量
              </h2>
              <p className="text-gray-600">选择处理变量、结果变量和协变量，然后运行因果推断分析</p>
            </div>
            <button
              onClick={() => navigate('/')}
              className="btn-secondary flex items-center gap-2"
            >
              <ArrowLeft className="w-4 h-4" />
              返回数据
            </button>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="space-y-6">
              <div className="card">
                <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
                  <Target className="w-5 h-5 text-accent-500" />
                  分析方法
                </h3>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    onClick={() => setMethod('psm')}
                    className={`p-4 rounded-xl border-2 text-left transition-all ${
                      method === 'psm'
                        ? 'border-primary-500 bg-primary-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <Layers className={`w-5 h-5 ${method === 'psm' ? 'text-primary-600' : 'text-gray-400'}`} />
                      <span className={`font-semibold ${method === 'psm' ? 'text-primary-700' : 'text-gray-700'}`}>
                        倾向性匹配
                      </span>
                    </div>
                    <p className="text-xs text-gray-500">
                      PSM - 通过倾向得分匹配处理组和对照组
                    </p>
                    {method === 'psm' && (
                      <CheckCircle2 className="w-5 h-5 text-primary-500 mt-2" />
                    )}
                  </button>
                  <button
                    onClick={() => setMethod('did')}
                    className={`p-4 rounded-xl border-2 text-left transition-all ${
                      method === 'did'
                        ? 'border-primary-500 bg-primary-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <TrendingUp className={`w-5 h-5 ${method === 'did' ? 'text-primary-600' : 'text-gray-400'}`} />
                      <span className={`font-semibold ${method === 'did' ? 'text-primary-700' : 'text-gray-700'}`}>
                        双重差分
                      </span>
                    </div>
                    <p className="text-xs text-gray-500">
                      DID - 利用时间维度的准实验设计
                    </p>
                    {method === 'did' && (
                      <CheckCircle2 className="w-5 h-5 text-primary-500 mt-2" />
                    )}
                  </button>
                </div>
              </div>

              <div className="card">
                <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
                  <Target className="w-5 h-5 text-data-red" />
                  处理变量 (Treatment)
                </h3>
                <p className="text-sm text-gray-500 mb-3">
                  表示是否接受处理的二元变量 (0=对照组, 1=处理组)
                </p>
                <select
                  value={treatment || ''}
                  onChange={(e) => setTreatment(e.target.value || null)}
                  className="select-field"
                >
                  <option value="">请选择处理变量...</option>
                  {binaryColumns.map(col => (
                    <option key={col} value={col}>{col}</option>
                  ))}
                </select>
                {treatment && (
                  <p className="mt-2 text-sm text-green-600 flex items-center gap-1">
                    <CheckCircle2 className="w-4 h-4" />
                    已选择: {treatment}
                  </p>
                )}
              </div>

              <div className="card">
                <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-data-green" />
                  结果变量 (Outcome)
                </h3>
                <p className="text-sm text-gray-500 mb-3">
                  您关心的处理效果所影响的结果变量
                </p>
                <select
                  value={outcome || ''}
                  onChange={(e) => setOutcome(e.target.value || null)}
                  className="select-field"
                >
                  <option value="">请选择结果变量...</option>
                  {numericColumns.map(col => (
                    <option key={col} value={col}>{col}</option>
                  ))}
                </select>
                {outcome && (
                  <p className="mt-2 text-sm text-green-600 flex items-center gap-1">
                    <CheckCircle2 className="w-4 h-4" />
                    已选择: {outcome}
                  </p>
                )}
              </div>

              {method === 'did' && (
                <div className="card">
                  <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
                    <Clock className="w-5 h-5 text-data-purple" />
                    时间变量 (Time)
                  </h3>
                  <p className="text-sm text-gray-500 mb-3">
                    表示观测时间点的变量（用于平行趋势检验）
                  </p>
                  <select
                    value={timeVariable || ''}
                    onChange={(e) => setTimeVariable(e.target.value || null)}
                    className="select-field"
                  >
                    <option value="">请选择时间变量...</option>
                    {numericColumns.map(col => (
                      <option key={col} value={col}>{col}</option>
                    ))}
                  </select>
                  {timeVariable && (
                    <p className="mt-2 text-sm text-green-600 flex items-center gap-1">
                      <CheckCircle2 className="w-4 h-4" />
                      已选择: {timeVariable}
                    </p>
                  )}
                </div>
              )}
            </div>

            <div className="space-y-6">
              <div className="card">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold text-gray-800 flex items-center gap-2">
                    <Sparkles className="w-5 h-5 text-accent-500" />
                    LASSO自动协变量筛选
                  </h3>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={useAutoSelection}
                      onChange={(e) => setUseAutoSelection(e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-500"></div>
                  </label>
                </div>

                {useAutoSelection && (
                  <div className="space-y-4 mb-4">
                    <p className="text-sm text-gray-500 flex items-start gap-2">
                      <Info className="w-4 h-4 mt-0.5 flex-shrink-0" />
                      使用L1正则化自动选择重要的协变量，减少维度和遗漏变量偏差
                    </p>
                    <div className="grid grid-cols-2 gap-2">
                      {lassoMethodOptions.map((opt) => (
                        <button
                          key={opt.value}
                          onClick={() => setLassoMethod(opt.value as LassoMethod)}
                          className={`p-3 rounded-lg border text-left transition-all ${
                            lassoMethod === opt.value
                              ? 'border-accent-400 bg-accent-50'
                              : 'border-gray-200 hover:border-gray-300'
                          }`}
                        >
                          <p className={`text-sm font-medium ${
                            lassoMethod === opt.value ? 'text-accent-700' : 'text-gray-700'
                          }`}>
                            {opt.label}
                          </p>
                          <p className="text-xs text-gray-500">{opt.desc}</p>
                        </button>
                      ))}
                    </div>
                    <button
                      onClick={handleAutoSelect}
                      disabled={!treatment || !outcome || availableCovariates.length === 0 || isAutoSelecting}
                      className="w-full btn-secondary text-sm"
                    >
                      {isAutoSelecting ? (
                        <>
                          <span className="inline-block w-4 h-4 border-2 border-primary-500 border-t-transparent rounded-full animate-spin mr-2" />
                          自动筛选中...
                        </>
                      ) : (
                        '预览自动选择结果'
                      )}
                    </button>
                  </div>
                )}

                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold text-gray-800 flex items-center gap-2">
                    <Layers className="w-5 h-5 text-data-blue" />
                    协变量 (Covariates)
                  </h3>
                  <div className="flex gap-2">
                    <button
                      onClick={selectAllCovariates}
                      className="text-xs text-primary-600 hover:text-primary-700 font-medium"
                    >
                      全选
                    </button>
                    <span className="text-gray-300">|</span>
                    <button
                      onClick={clearAllCovariates}
                      className="text-xs text-gray-500 hover:text-gray-700 font-medium"
                    >
                      清空
                    </button>
                  </div>
                </div>
                <p className="text-sm text-gray-500 mb-4">
                  选择需要控制的混淆变量（影响处理分配和结果的变量）
                </p>
                <div className="overflow-y-auto max-h-64 scrollbar-thin space-y-2 pr-2">
                  {availableCovariates.map(col => {
                    const info = columnInfo.find(c => c.name === col);
                    return (
                      <button
                        key={col}
                        onClick={() => toggleCovariate(col)}
                        className={`w-full p-3 rounded-lg border text-left transition-all flex items-center justify-between ${
                          covariates.includes(col)
                            ? 'border-primary-300 bg-primary-50'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        <div>
                          <span className={`font-medium ${
                            covariates.includes(col) ? 'text-primary-700' : 'text-gray-700'
                          }`}>
                            {col}
                          </span>
                          {info && (
                            <span className="ml-2 text-xs text-gray-400">
                              {info.type === 'numeric' ? '数值' : info.type === 'binary' ? '二元' : '分类'}
                            </span>
                          )}
                        </div>
                        {covariates.includes(col) && (
                          <CheckCircle2 className="w-5 h-5 text-primary-500" />
                        )}
                      </button>
                    );
                  })}
                </div>
                <div className="mt-4 pt-4 border-t border-gray-100">
                  <p className="text-sm text-gray-500">
                    已选择 <span className="font-semibold text-primary-600">{covariates.length}</span> 个协变量
                    {useAutoSelection && (
                      <span className="ml-2 text-accent-600">
                        (将使用LASSO自动筛选)
                      </span>
                    )}
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-8 flex justify-end">
            <button
              onClick={handleRunAnalysis}
              disabled={!canRunAnalysis || isAnalyzing}
              className="btn-accent flex items-center gap-2 text-lg px-8 py-3"
            >
              {isAnalyzing ? (
                <>
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  分析中...
                </>
              ) : (
                <>
                  <Play className="w-5 h-5" />
                  运行因果推断分析
                  <ArrowRight className="w-5 h-5" />
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
