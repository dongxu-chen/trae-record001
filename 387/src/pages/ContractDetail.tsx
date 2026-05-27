import { useEffect, useState, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, FileCode, Play, CheckCircle, AlertCircle, Code, Gauge, Plus, Minus } from 'lucide-react';
import { api } from '@/utils/api';

export default function ContractDetail() {
  const { address } = useParams<{ address: string }>();
  const [contract, setContract] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<'code' | 'read' | 'write'>('code');
  const [source, setSource] = useState('');
  const [compilerVersion, setCompilerVersion] = useState('v0.8.19');
  const [contractName, setContractName] = useState('Contract');
  const [verifying, setVerifying] = useState(false);
  const [verifyResult, setVerifyResult] = useState<any>(null);
  const [selectedMethod, setSelectedMethod] = useState('');
  const [methodParams, setMethodParams] = useState('');
  const [callResult, setCallResult] = useState<any>(null);
  const [calling, setCalling] = useState(false);
  const [gasEstimate, setGasEstimate] = useState<string>('');
  const [gasLimit, setGasLimit] = useState<string>('');
  const [gasBuffer, setGasBuffer] = useState<number>(10);
  const [estimatingGas, setEstimatingGas] = useState(false);

  const estimateGasForMethod = useCallback(async () => {
    if (!selectedMethod || !contract?.verified || !contract?.abi) return;
    
    setEstimatingGas(true);
    try {
      const params = methodParams ? methodParams.split(',').map((p) => p.trim()) : [];
      const result = await api.estimateGas(address!, {
        abi: contract.abi,
        method: selectedMethod,
        params,
      });
      
      if (result.success && result.gasEstimate) {
        const estimated = BigInt(result.gasEstimate);
        const bufferMultiplier = BigInt(100 + gasBuffer);
        const withBuffer = (estimated * bufferMultiplier) / 100n;
        setGasEstimate(result.gasEstimate);
        setGasLimit(withBuffer.toString());
      }
    } catch (e) {
      console.error('Gas estimation failed:', e);
    } finally {
      setEstimatingGas(false);
    }
  }, [address, selectedMethod, contract, methodParams, gasBuffer]);

  useEffect(() => {
    if (selectedMethod && contract?.verified) {
      estimateGasForMethod();
    }
  }, [selectedMethod, methodParams, contract, estimateGasForMethod]);

  const adjustGasLimit = (delta: number) => {
    if (!gasLimit) return;
    const current = BigInt(gasLimit);
    const adjusted = current + BigInt(delta);
    if (adjusted > 0n) {
      setGasLimit(adjusted.toString());
    }
  };

  const adjustGasBuffer = (delta: number) => {
    const newBuffer = Math.max(0, Math.min(100, gasBuffer + delta));
    setGasBuffer(newBuffer);
    
    if (gasEstimate) {
      const estimated = BigInt(gasEstimate);
      const bufferMultiplier = BigInt(100 + newBuffer);
      const withBuffer = (estimated * bufferMultiplier) / 100n;
      setGasLimit(withBuffer.toString());
    }
  };

  useEffect(() => {
    const loadData = async () => {
      try {
        const data = await api.getContract(address!);
        setContract(data);
      } catch (e) {
        console.error('Failed to load contract:', e);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, [address]);

  const handleVerify = async () => {
    if (!source.trim()) return;
    setVerifying(true);
    setVerifyResult(null);
    try {
      const result = await api.verifyContract({
        address: address!,
        source,
        compilerVersion,
        name: contractName,
        optimization: true,
        runs: 200,
      });
      setVerifyResult(result);
    } catch (e) {
      setVerifyResult({ verified: false, message: (e as Error).message });
    } finally {
      setVerifying(false);
    }
  };

  const handleRead = async () => {
    if (!selectedMethod || !contract?.verified) return;
    setCalling(true);
    setCallResult(null);
    try {
      const params = methodParams ? methodParams.split(',').map((p) => p.trim()) : [];
      const result = await api.readContract(address!, {
        abi: contract.abi,
        method: selectedMethod,
        params,
      });
      setCallResult(result);
    } catch (e) {
      setCallResult({ success: false, error: (e as Error).message });
    } finally {
      setCalling(false);
    }
  };

  if (loading) {
    return <div className="text-center text-slate-500 py-20">加载中...</div>;
  }

  if (!contract || contract.code === '0x') {
    return (
      <div className="text-center py-20">
        <p className="text-slate-400 mb-4">该地址不是合约地址</p>
        <Link to="/" className="text-cyan-400 hover:text-cyan-300">返回首页</Link>
      </div>
    );
  }

  const abiMethods = contract.verified && contract.abi
    ? JSON.parse(contract.abi).filter((item: any) => item.type === 'function')
    : [];

  return (
    <div className="space-y-6">
      <Link to="/" className="inline-flex items-center gap-2 text-slate-400 hover:text-slate-200 transition-colors">
        <ArrowLeft className="w-4 h-4" />
        返回首页
      </Link>

      <div className="p-6 bg-slate-800/30 backdrop-blur-sm border border-slate-700/50 rounded-xl">
        <div className="flex items-start justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-purple-500/10 flex items-center justify-center">
              <FileCode className="w-6 h-6 text-purple-400" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white font-mono break-all">{address}</h2>
              <div className="flex items-center gap-2 mt-1">
                {contract.verified ? (
                  <span className="flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-emerald-500/20 text-emerald-400">
                    <CheckCircle className="w-3 h-3" /> 已验证
                  </span>
                ) : (
                  <span className="flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-amber-500/20 text-amber-400">
                    <AlertCircle className="w-3 h-3" /> 未验证
                  </span>
                )}
                {contract.name && <span className="text-sm text-slate-400">{contract.name}</span>}
              </div>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-1 mb-6 border-b border-slate-700/50">
          {['code', 'read', 'write'].map((t) => (
            <button
              key={t}
              onClick={() => setTab(t as any)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                tab === t
                  ? 'border-cyan-400 text-cyan-400'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              {t === 'code' ? '合约代码' : t === 'read' ? '读取合约' : '写入合约'}
            </button>
          ))}
        </div>

        {tab === 'code' && (
          <div className="space-y-4">
            {!contract.verified && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-slate-400 mb-2">合约名称</label>
                  <input
                    type="text"
                    value={contractName}
                    onChange={(e) => setContractName(e.target.value)}
                    className="w-full px-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-sm text-slate-100 focus:outline-none focus:border-cyan-500/50"
                  />
                </div>
                <div>
                  <label className="block text-sm text-slate-400 mb-2">编译器版本</label>
                  <select
                    value={compilerVersion}
                    onChange={(e) => setCompilerVersion(e.target.value)}
                    className="w-full px-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-sm text-slate-100 focus:outline-none focus:border-cyan-500/50"
                  >
                    <option value="v0.8.24">v0.8.24</option>
                    <option value="v0.8.19">v0.8.19</option>
                    <option value="v0.8.15">v0.8.15</option>
                    <option value="v0.8.12">v0.8.12</option>
                    <option value="v0.8.9">v0.8.9</option>
                    <option value="v0.8.0">v0.8.0</option>
                    <option value="v0.7.6">v0.7.6</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-slate-400 mb-2">合约源代码</label>
                  <textarea
                    value={source}
                    onChange={(e) => setSource(e.target.value)}
                    rows={12}
                    placeholder="// SPDX-License-Identifier: MIT&#10;pragma solidity ^0.8.0;&#10;&#10;contract MyContract {&#10;    // ...&#10;}"
                    className="w-full px-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-sm text-slate-100 font-mono focus:outline-none focus:border-cyan-500/50 resize-none"
                  />
                </div>
                <button
                  onClick={handleVerify}
                  disabled={verifying || !source.trim()}
                  className="px-6 py-2 bg-cyan-500/20 text-cyan-400 rounded-lg text-sm font-medium hover:bg-cyan-500/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {verifying ? '验证中...' : '验证合约'}
                </button>
                {verifyResult && (
                  <div className={`p-4 rounded-lg ${verifyResult.verified ? 'bg-emerald-500/10 border border-emerald-500/30' : 'bg-red-500/10 border border-red-500/30'}`}>
                    <p className={`text-sm ${verifyResult.verified ? 'text-emerald-400' : 'text-red-400'}`}>
                      {verifyResult.message}
                    </p>
                  </div>
                )}
              </div>
            )}
            {contract.verified && contract.source && (
              <div className="p-4 bg-slate-700/30 rounded-lg border border-slate-600/30">
                <div className="flex items-center gap-2 mb-2 text-sm text-slate-400">
                  <Code className="w-4 h-4" />
                  已验证源代码
                </div>
                <pre className="text-xs text-slate-300 font-mono overflow-auto max-h-96 whitespace-pre-wrap">
                  {contract.source}
                </pre>
              </div>
            )}
            <div className="p-4 bg-slate-700/30 rounded-lg border border-slate-600/30">
              <div className="text-sm text-slate-400 mb-2">合约字节码 (Bytecode)</div>
              <code className="text-xs text-slate-500 font-mono break-all">{contract.code.slice(0, 100)}...</code>
            </div>
          </div>
        )}

        {(tab === 'read' || tab === 'write') && (
          <div className="space-y-4">
            {!contract.verified ? (
              <p className="text-sm text-amber-400">请先验证合约源代码以启用合约交互功能</p>
            ) : abiMethods.length === 0 ? (
              <p className="text-sm text-slate-400">未发现可用的合约方法</p>
            ) : (
              <>
                <div>
                  <label className="block text-sm text-slate-400 mb-2">选择方法</label>
                  <select
                    value={selectedMethod}
                    onChange={(e) => setSelectedMethod(e.target.value)}
                    className="w-full px-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-sm text-slate-100 focus:outline-none focus:border-cyan-500/50"
                  >
                    <option value="">选择方法...</option>
                    {abiMethods.map((m: any, idx: number) => (
                      <option key={idx} value={m.name}>
                        {m.name}({m.inputs.map((i: any) => i.type).join(', ')})
                      </option>
                    ))}
                  </select>
                </div>
                {selectedMethod && (
                  <div>
                    <label className="block text-sm text-slate-400 mb-2">参数 (逗号分隔)</label>
                    <input
                      type="text"
                      value={methodParams}
                      onChange={(e) => setMethodParams(e.target.value)}
                      placeholder="参数1, 参数2, ..."
                      className="w-full px-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-sm text-slate-100 focus:outline-none focus:border-cyan-500/50"
                    />
                  </div>
                )}
                {selectedMethod && (
                  <div className="p-4 bg-slate-700/20 border border-slate-600/30 rounded-lg space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Gauge className="w-4 h-4 text-cyan-400" />
                        <span className="text-sm font-medium text-slate-300">Gas 估算</span>
                      </div>
                      <button
                        onClick={estimateGasForMethod}
                        disabled={estimatingGas}
                        className="text-xs text-cyan-400 hover:text-cyan-300 disabled:opacity-50"
                      >
                        {estimatingGas ? '估算中...' : '重新估算'}
                      </button>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <div className="text-xs text-slate-500 mb-1">估算值</div>
                        <div className="text-sm text-slate-300 font-mono">
                          {gasEstimate ? `${BigInt(gasEstimate).toLocaleString()} gas` : '—'}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-slate-500 mb-1">缓冲</div>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => adjustGasBuffer(-5)}
                            className="w-5 h-5 flex items-center justify-center rounded bg-slate-600/50 text-slate-400 hover:bg-slate-600 hover:text-slate-200"
                          >
                            <Minus className="w-3 h-3" />
                          </button>
                          <span className="text-sm text-cyan-400 font-mono w-12 text-center">+{gasBuffer}%</span>
                          <button
                            onClick={() => adjustGasBuffer(5)}
                            className="w-5 h-5 flex items-center justify-center rounded bg-slate-600/50 text-slate-400 hover:bg-slate-600 hover:text-slate-200"
                          >
                            <Plus className="w-3 h-3" />
                          </button>
                        </div>
                      </div>
                    </div>
                    <div>
                      <label className="text-xs text-slate-500 mb-1 block">Gas 限制 (可微调)</label>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => adjustGasLimit(-1000)}
                          className="w-8 h-8 flex items-center justify-center rounded-lg bg-slate-600/50 text-slate-400 hover:bg-slate-600 hover:text-slate-200"
                        >
                          <Minus className="w-4 h-4" />
                        </button>
                        <input
                          type="text"
                          value={gasLimit}
                          onChange={(e) => {
                            const val = e.target.value.replace(/[^0-9]/g, '');
                            setGasLimit(val);
                          }}
                          className="flex-1 px-3 py-1.5 bg-slate-700/50 border border-slate-600 rounded-lg text-sm text-slate-100 font-mono text-center focus:outline-none focus:border-cyan-500/50"
                        />
                        <button
                          onClick={() => adjustGasLimit(1000)}
                          className="w-8 h-8 flex items-center justify-center rounded-lg bg-slate-600/50 text-slate-400 hover:bg-slate-600 hover:text-slate-200"
                        >
                          <Plus className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                )}
                {selectedMethod && (
                  <button
                    onClick={handleRead}
                    disabled={calling}
                    className="flex items-center gap-2 px-6 py-2 bg-cyan-500/20 text-cyan-400 rounded-lg text-sm font-medium hover:bg-cyan-500/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Play className="w-4 h-4" />
                    {calling ? '执行中...' : '执行'}
                  </button>
                )}
                {callResult && (
                  <div className="p-4 bg-slate-700/30 rounded-lg border border-slate-600/30">
                    <div className="text-sm text-slate-400 mb-2">返回结果</div>
                    <pre className="text-xs text-slate-300 font-mono overflow-auto">
                      {JSON.stringify(callResult, null, 2)}
                    </pre>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
