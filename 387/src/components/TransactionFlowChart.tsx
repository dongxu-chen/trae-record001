import { useEffect, useRef, useMemo } from 'react';
import * as echarts from 'echarts';
import { ArrowRightLeft } from 'lucide-react';

interface TransactionFlow {
  from: string;
  to: string;
  value: string;
  timestamp: number;
}

interface TransactionFlowChartProps {
  transactions: TransactionFlow[];
  currentAddress?: string;
  height?: number;
}

function shortenAddress(addr: string): string {
  if (!addr) return 'Unknown';
  if (addr.length <= 14) return addr;
  return `${addr.slice(0, 6)}...${addr.slice(-4)}`;
}

export default function TransactionFlowChart({
  transactions,
  currentAddress,
  height = 400,
}: TransactionFlowChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  const chartData = useMemo(() => {
    if (!transactions.length) return { nodes: [], links: [] };

    const addressSet = new Set<string>();
    const flowMap = new Map<string, number>();

    transactions.forEach((tx) => {
      if (!tx.from || !tx.to) return;
      addressSet.add(tx.from);
      addressSet.add(tx.to);
      const key = `${tx.from}->${tx.to}`;
      const value = Number(tx.value) / 1e18;
      flowMap.set(key, (flowMap.get(key) || 0) + value);
    });

    const nodes = Array.from(addressSet).map((addr) => ({
      name: shortenAddress(addr),
      fullName: addr,
      itemStyle: {
        color: currentAddress && addr.toLowerCase() === currentAddress.toLowerCase()
          ? '#06b6d4'
          : addr.toLowerCase().startsWith('0x0000000000000000000000000000000000000000')
          ? '#64748b'
          : '#8b5cf6',
      },
    }));

    const links = Array.from(flowMap.entries()).map(([key, value]) => {
      const [from, to] = key.split('->');
      return {
        source: shortenAddress(from),
        target: shortenAddress(to),
        value: Number(value.toFixed(6)),
        lineStyle: {
          color: currentAddress && from.toLowerCase() === currentAddress.toLowerCase()
            ? 'rgba(6, 182, 212, 0.4)'
            : currentAddress && to.toLowerCase() === currentAddress.toLowerCase()
            ? 'rgba(139, 92, 246, 0.4)'
            : 'rgba(148, 163, 184, 0.3)',
        },
      };
    });

    return { nodes, links };
  }, [transactions, currentAddress]);

  useEffect(() => {
    if (!chartRef.current || !chartData.nodes.length) return;

    if (chartInstance.current) {
      chartInstance.current.dispose();
    }

    const chart = echarts.init(chartRef.current);
    chartInstance.current = chart;

    const option: echarts.EChartsOption = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(15, 23, 42, 0.95)',
        borderColor: 'rgba(6, 182, 212, 0.3)',
        textStyle: { color: '#e2e8f0', fontSize: 12 },
        formatter: (params: any) => {
          if (params.dataType === 'edge') {
            return `
              <div style="font-family: monospace">
                <div style="color: #94a3b8">${params.data.source} → ${params.data.target}</div>
                <div style="color: #f59e0b; margin-top: 4px">${params.data.value.toFixed(6)} ETH</div>
              </div>
            `;
          }
          const nodeData = chartData.nodes.find((n) => n.name === params.name);
          return `
            <div style="font-family: monospace">
              <div style="color: #94a3b8">地址</div>
              <div style="color: #e2e8f0; word-break: break-all">${nodeData?.fullName || params.name}</div>
            </div>
          `;
        },
      },
      series: [
        {
          type: 'sankey',
          layout: 'none',
          emphasis: { focus: 'adjacency' },
          nodeAlign: 'justify',
          nodeWidth: 20,
          nodeGap: 12,
          layoutIterations: 32,
          data: chartData.nodes,
          links: chartData.links,
          label: {
            color: '#94a3b8',
            fontSize: 11,
            fontFamily: 'monospace',
          },
          lineStyle: {
            color: 'gradient',
            curveness: 0.5,
            opacity: 0.6,
          },
          itemStyle: {
            borderWidth: 0,
          },
        },
      ],
    };

    chart.setOption(option);

    const handleResize = () => chart.resize();
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.dispose();
    };
  }, [chartData]);

  return (
    <div className="p-6 bg-slate-800/30 backdrop-blur-sm border border-slate-700/50 rounded-xl">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <ArrowRightLeft className="w-5 h-5 text-emerald-400" />
          <h3 className="text-lg font-semibold text-white">资金流向图</h3>
        </div>
        <div className="flex items-center gap-4 text-xs text-slate-500">
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded-sm bg-cyan-500" />
            <span>当前地址</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded-sm bg-violet-500" />
            <span>其他地址</span>
          </div>
        </div>
      </div>

      {chartData.nodes.length > 0 ? (
        <div ref={chartRef} style={{ height }} />
      ) : (
        <div className="h-[400px] flex items-center justify-center text-slate-500">
          暂无交易数据
        </div>
      )}
    </div>
  );
}
