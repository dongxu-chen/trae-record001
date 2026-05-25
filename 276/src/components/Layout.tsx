import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom';
import { LayoutDashboard, BarChart3, Settings, TrendingUp } from 'lucide-react';

export default function Layout() {
  const location = useLocation();
  const navigate = useNavigate();
  
  const boardIdMatch = location.pathname.match(/\/board\/([^/]+)/);
  const currentBoardId = boardIdMatch?.[1];

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <Link to="/" className="flex items-center gap-2">
              <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
                <LayoutDashboard className="w-5 h-5 text-white" />
              </div>
              <span className="text-xl font-bold text-gray-900">任务看板</span>
            </Link>
            
            <div className="flex items-center gap-1">
              <Link
                to="/automation"
                className={`btn btn-ghost flex items-center gap-2 text-sm ${
                  location.pathname === '/automation' ? 'bg-gray-100' : ''
                }`}
              >
                <Settings className="w-4 h-4" />
                自动化规则
              </Link>
              <Link
                to="/efficiency"
                className={`btn btn-ghost flex items-center gap-2 text-sm ${
                  location.pathname === '/efficiency' ? 'bg-gray-100' : ''
                }`}
              >
                <TrendingUp className="w-4 h-4" />
                效能报表
              </Link>
            </div>
            
            {currentBoardId && (
              <div className="flex items-center gap-2">
                <Link
                  to={`/board/${currentBoardId}`}
                  className={`btn btn-ghost flex items-center gap-2 ${
                    location.pathname === `/board/${currentBoardId}` ? 'bg-gray-100' : ''
                  }`}
                >
                  <LayoutDashboard className="w-4 h-4" />
                  看板视图
                </Link>
                <Link
                  to={`/board/${currentBoardId}/gantt`}
                  className={`btn btn-ghost flex items-center gap-2 ${
                    location.pathname === `/board/${currentBoardId}/gantt` ? 'bg-gray-100' : ''
                  }`}
                >
                  <BarChart3 className="w-4 h-4" />
                  甘特图
                </Link>
              </div>
            )}
          </div>
        </div>
      </header>
      
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>
    </div>
  );
}
