import { NavLink, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { QrCode, Layers, Zap, BarChart3, Bookmark, Sparkles, TrendingUp, Settings } from 'lucide-react';
import { cn } from '@/lib/utils';

const navItems = [
  { path: '/', label: '生成器', icon: QrCode },
  { path: '/art', label: '艺术二维码', icon: Sparkles },
  { path: '/batch', label: '批量生成', icon: Layers },
  { path: '/dynamic', label: '动态二维码', icon: Zap },
  { path: '/analysis', label: '落地页分析', icon: TrendingUp },
  { path: '/statistics', label: '统计中心', icon: BarChart3 },
  { path: '/management', label: '管理平台', icon: Settings },
  { path: '/my-codes', label: '我的二维码', icon: Bookmark },
];

export default function Navbar() {
  return (
    <motion.nav
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      className="sticky top-0 z-40 bg-slate-950/80 backdrop-blur-xl border-b border-slate-800/50"
    >
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <Link to="/" className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-400 flex items-center justify-center shadow-lg shadow-blue-500/25">
              <QrCode size={22} className="text-white" />
            </div>
            <div>
              <h1 className="font-bold text-lg text-white">QR Code Pro</h1>
              <p className="text-xs text-slate-500">专业二维码生成器</p>
            </div>
          </Link>

          <div className="hidden md:flex items-center gap-1 bg-slate-900/50 rounded-2xl p-1 border border-slate-800/50">
            {navItems.map(({ path, label, icon: Icon }) => (
              <NavLink
                key={path}
                to={path}
                end={path === '/'}
                className={({ isActive }) =>
                  cn(
                    'relative flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all',
                    isActive
                      ? 'text-white'
                      : 'text-slate-400 hover:text-slate-200'
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    {isActive && (
                      <motion.div
                        layoutId="activeNav"
                        className="absolute inset-0 rounded-xl bg-gradient-to-r from-blue-600/20 to-cyan-500/20 border border-blue-500/30"
                        transition={{ type: 'spring', bounce: 0.2, duration: 0.6 }}
                      />
                    )}
                    <Icon size={16} className="relative z-10" />
                    <span className="relative z-10">{label}</span>
                  </>
                )}
              </NavLink>
            ))}
          </div>

          <div className="md:hidden flex items-center">
            <span className="text-sm text-slate-400">扫码工具</span>
          </div>
        </div>

        <div className="md:hidden flex items-center gap-1 pb-3 overflow-x-auto">
          {navItems.map(({ path, label, icon: Icon }) => (
            <NavLink
              key={path}
              to={path}
              end={path === '/'}
              className={({ isActive }) =>
                cn(
                  'flex flex-col items-center gap-1 px-3 py-2 rounded-xl text-xs font-medium whitespace-nowrap transition-all',
                  isActive
                    ? 'text-white bg-blue-600/20 border border-blue-500/30'
                    : 'text-slate-400'
                )
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </div>
      </div>
    </motion.nav>
  );
}
