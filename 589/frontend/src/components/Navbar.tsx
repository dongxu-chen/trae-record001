import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Search, Bell, Heart, User, Menu, X, TrendingDown } from 'lucide-react';
import { useAppStore } from '../store/useAppStore';

export default function Navbar() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchInput, setSearchInput] = useState('');
  const { searchQuery, setSearchQuery, notifications, sidebarOpen, setSidebarOpen } = useAppStore();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchInput.trim()) {
      setSearchQuery(searchInput);
      navigate(`/search?q=${encodeURIComponent(searchInput)}`);
    }
  };

  React.useEffect(() => {
    if (location.pathname === '/search') {
      const params = new URLSearchParams(location.search);
      const q = params.get('q');
      if (q) setSearchInput(q);
    }
  }, [location]);

  const navItems = [
    { path: '/', label: '首页', icon: TrendingDown },
    { path: '/products/hot', label: '热门降价', icon: TrendingDown },
    { path: '/products/coupons', label: '优惠券', icon: Bell },
    { path: '/user/favorites', label: '我的关注', icon: Heart },
    { path: '/user/alerts', label: '降价提醒', icon: Bell },
  ];

  return (
    <nav className="bg-gradient-to-r from-blue-900 to-blue-800 text-white shadow-lg sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-4">
            <button
              className="lg:hidden p-2 hover:bg-blue-700 rounded-lg transition-colors"
              onClick={() => setSidebarOpen(!sidebarOpen)}
            >
              {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
            <Link to="/" className="flex items-center space-x-2">
              <TrendingDown className="text-orange-400" size={28} />
              <span className="text-xl font-bold">比价达人</span>
            </Link>
          </div>

          <div className="hidden md:flex flex-1 max-w-2xl mx-8">
            <form onSubmit={handleSearch} className="w-full relative">
              <input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="搜索商品，如 iPhone 15、MacBook..."
                className="w-full px-4 py-2 pr-12 rounded-full bg-white/10 border border-white/20 text-white placeholder-white/60 focus:outline-none focus:ring-2 focus:ring-orange-400 focus:bg-white/20 transition-all"
              />
              <button
                type="submit"
                className="absolute right-2 top-1/2 -translate-y-1/2 p-2 hover:bg-white/10 rounded-full transition-colors"
              >
                <Search size={20} />
              </button>
            </form>
          </div>

          <div className="flex items-center space-x-2">
            <Link
              to="/user/favorites"
              className="p-2 hover:bg-blue-700 rounded-full transition-colors relative"
            >
              <Heart size={20} />
            </Link>
            <button
              onClick={() => navigate('/user/alerts')}
              className="p-2 hover:bg-blue-700 rounded-full transition-colors relative"
            >
              <Bell size={20} />
              {notifications.length > 0 && (
                <span className="absolute -top-1 -right-1 bg-red-500 text-xs w-5 h-5 rounded-full flex items-center justify-center font-bold animate-pulse">
                  {notifications.length}
                </span>
              )}
            </button>
            <button className="p-2 hover:bg-blue-700 rounded-full transition-colors">
              <User size={20} />
            </button>
          </div>
        </div>

        <div className="md:hidden pb-3">
          <form onSubmit={handleSearch} className="w-full relative">
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="搜索商品..."
              className="w-full px-4 py-2 pr-12 rounded-full bg-white/10 border border-white/20 text-white placeholder-white/60 focus:outline-none focus:ring-2 focus:ring-orange-400"
            />
            <button
              type="submit"
              className="absolute right-2 top-1/2 -translate-y-1/2 p-2 hover:bg-white/10 rounded-full"
            >
              <Search size={18} />
            </button>
          </form>
        </div>

        <div className="hidden lg:flex items-center space-x-1 pb-2 overflow-x-auto">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`px-4 py-1.5 rounded-full text-sm font-medium transition-all whitespace-nowrap ${
                location.pathname === item.path
                  ? 'bg-orange-500 text-white'
                  : 'text-white/80 hover:bg-white/10'
              }`}
            >
              {item.label}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
}
