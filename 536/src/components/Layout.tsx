import { Outlet } from 'react-router-dom';
import Sidebar from '@/components/Sidebar';

export default function Layout() {
  return (
    <div className="min-h-screen bg-monitor-bg font-sans text-monitor-text">
      <Sidebar />
      <main className="ml-60 min-h-screen">
        <Outlet />
      </main>
    </div>
  );
}
