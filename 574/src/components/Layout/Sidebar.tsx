import { Search, Network, TrendingUp, Award, BookOpen, Menu, X, Sparkles, Users, LineChart } from 'lucide-react';
import { useAppStore } from '@/store';

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

const navItems = [
  { id: 'search', label: '论文搜索', icon: Search },
  { id: 'network', label: '引用网络', icon: Network },
  { id: 'influence', label: '影响力分析', icon: Award },
  { id: 'trends', label: '研究趋势', icon: TrendingUp },
  { id: 'recommendations', label: '论文推荐', icon: Sparkles },
  { id: 'collaboration', label: '合作者发现', icon: Users },
  { id: 'prediction', label: '影响力预测', icon: LineChart },
];

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const { currentPage, setCurrentPage } = useAppStore();

  return (
    <aside
      className={`fixed left-0 top-0 h-full bg-dark-800/90 backdrop-blur-xl border-r border-primary-500/20 z-40 transition-all duration-300 ${
        collapsed ? 'w-20' : 'w-64'
      }`}
    >
      <div className="flex items-center justify-between p-4 border-b border-primary-500/20">
        {!collapsed && (
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent-blue to-accent-green flex items-center justify-center">
              <BookOpen className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="font-display font-bold text-lg text-gradient">
                CitationNet
              </h1>
              <p className="text-xs text-dark-400">学术引用分析</p>
            </div>
          </div>
        )}
        {collapsed && (
          <div className="w-10 h-10 mx-auto rounded-xl bg-gradient-to-br from-accent-blue to-accent-green flex items-center justify-center">
            <BookOpen className="w-5 h-5 text-white" />
          </div>
        )}
        <button
          onClick={onToggle}
          className="p-2 rounded-lg hover:bg-dark-700 transition-colors text-dark-400 hover:text-white"
        >
          {collapsed ? <Menu className="w-5 h-5" /> : <X className="w-5 h-5" />}
        </button>
      </div>

      <nav className="p-4 space-y-2">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentPage === item.id;

          return (
            <button
              key={item.id}
              onClick={() => setCurrentPage(item.id)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group ${
                isActive
                  ? 'bg-gradient-to-r from-accent-blue/20 to-accent-green/10 text-accent-blue border border-accent-blue/30 shadow-lg shadow-accent-blue/10'
                  : 'text-dark-400 hover:text-white hover:bg-dark-700/50'
              }`}
            >
              <Icon
                className={`w-5 h-5 flex-shrink-0 transition-transform ${
                  isActive ? 'text-accent-blue' : 'group-hover:scale-110'
                }`}
              />
              {!collapsed && (
                <span className="font-medium whitespace-nowrap">{item.label}</span>
              )}
              {isActive && !collapsed && (
                <div className="ml-auto w-2 h-2 rounded-full bg-accent-blue animate-pulse" />
              )}
            </button>
          );
        })}
      </nav>

      {!collapsed && (
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-primary-500/20">
          <div className="glass rounded-xl p-4">
            <p className="text-xs text-dark-400 mb-2">数据源</p>
            <div className="flex gap-2">
              <span className="px-2 py-1 text-xs rounded-full bg-accent-blue/20 text-accent-blue">
                Crossref
              </span>
              <span className="px-2 py-1 text-xs rounded-full bg-accent-green/20 text-accent-green">
                DBLP
              </span>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
