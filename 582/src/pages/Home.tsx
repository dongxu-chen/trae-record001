import { useNavigate } from 'react-router-dom';
import { Sparkles, Eye, Grid, Printer } from 'lucide-react';
import DecorativeDivider from '@/components/DecorativeDivider';

const FEATURES = [
  {
    icon: Sparkles,
    title: '模板系统',
    desc: '多种精美卡牌模板，支持自定义配色和布局',
  },
  {
    icon: Eye,
    title: '实时预览',
    desc: '所见即所得，编辑时即时渲染卡牌效果',
  },
  {
    icon: Grid,
    title: '批量生成',
    desc: '导入数据批量生成卡牌，大幅提升效率',
  },
  {
    icon: Printer,
    title: '打印导出',
    desc: '支持 PNG/JPG/PDF 多格式导出，适配打印需求',
  },
];

const DEMO_TEMPLATES = [
  {
    name: '暗夜骑士',
    colors: { primary: '#1a1a2e', secondary: '#16213e', background: '#0f3460', accent: '#e94560' },
  },
  {
    name: '金色传说',
    colors: { primary: '#2a2a1e', secondary: '#3d3522', background: '#1a1612', accent: '#d4a853' },
  },
  {
    name: '血月法师',
    colors: { primary: '#2a1020', secondary: '#3d1530', background: '#1a0a15', accent: '#8b2252' },
  },
];

export default function Home() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen relative overflow-hidden">
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-64 h-64 bg-gold-500/5 rounded-full blur-[100px] animate-pulse" />
        <div className="absolute bottom-1/3 right-1/4 w-80 h-80 bg-crimson-500/5 rounded-full blur-[120px] animate-pulse" />
        <div className="absolute top-1/2 left-1/2 w-96 h-96 bg-dark-700/30 rounded-full blur-[150px]" />
      </div>

      <div className="relative z-10 max-w-6xl mx-auto px-6 py-16">
        <div className="flex flex-col lg:flex-row items-center gap-12 mb-20">
          <div className="flex-1 text-center lg:text-left animate-fade-in-up">
            <h1 className="font-cinzel text-5xl lg:text-7xl font-bold mb-4 bg-gradient-to-r from-gold-400 via-gold-500 to-gold-600 bg-clip-text text-transparent">
              Card Forge
            </h1>
            <p className="font-cinzel text-xl lg:text-2xl text-parchment-200/80 mb-2">
              卡牌游戏生成器
            </p>
            <p className="font-crimson text-parchment-200/60 mb-8 max-w-md">
              在暗黑的锻造炉中，铸造属于你的卡牌。从模板到成品，从单卡到批量，Card Forge 为你提供完整的卡牌创作工具链。
            </p>
            <div className="flex gap-4 justify-center lg:justify-start">
              <button
                onClick={() => navigate('/editor')}
                className="metal-button-primary px-6 py-3 rounded"
              >
                开始创作
              </button>
              <button
                onClick={() => navigate('/templates')}
                className="metal-button px-6 py-3 rounded"
              >
                浏览模板
              </button>
            </div>
          </div>

          <div className="flex-1 flex justify-center items-end gap-4">
            {DEMO_TEMPLATES.map((tmpl, i) => (
              <div
                key={i}
                className="animate-float"
                style={{ animationDelay: `${i * 0.5}s` }}
              >
                <div
                  className="w-[120px] h-[168px] rounded-lg border-2 shadow-[0_0_15px_rgba(0,0,0,0.5)]"
                  style={{
                    background: `linear-gradient(135deg, ${tmpl.colors.primary}, ${tmpl.colors.secondary}, ${tmpl.colors.background})`,
                    borderColor: tmpl.colors.accent,
                    transform: `rotate(${(i - 1) * 5}deg)`,
                  }}
                >
                  <div className="flex flex-col items-center justify-center h-full p-2">
                    <div
                      className="w-8 h-8 rounded-full mb-2"
                      style={{ background: tmpl.colors.accent + '40', border: `1px solid ${tmpl.colors.accent}` }}
                    />
                    <span className="font-cinzel text-[9px]" style={{ color: tmpl.colors.accent }}>
                      {tmpl.name}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <DecorativeDivider />

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mt-12">
          {FEATURES.map((feature, i) => (
            <div
              key={i}
              className="animate-fade-in-up bg-dark-800/50 border border-dark-600 rounded-lg p-6 hover:border-gold-500/30 hover:shadow-[0_0_12px_rgba(212,168,83,0.15)] transition-all"
              style={{ animationDelay: `${i * 0.15}s` }}
            >
              <feature.icon size={28} className="text-gold-500 mb-3" />
              <h3 className="font-cinzel text-gold-400 text-sm mb-2">{feature.title}</h3>
              <p className="font-crimson text-parchment-200/60 text-sm">{feature.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
