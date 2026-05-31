import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import AppLayout from "@/components/Layout";
import Dashboard from "@/pages/Dashboard";
import DataSourceList from "@/pages/DataSourceList";
import TaskList from "@/pages/TaskList";
import TaskMonitor from "@/pages/TaskMonitor";
import Settings from "@/pages/Settings";

export default function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <Router>
        <Routes>
          <Route path="/" element={<AppLayout />}>
            <Route index element={<Dashboard />} />
            <Route path="datasource" element={<DataSourceList />} />
            <Route path="task" element={<TaskList />} />
            <Route path="task/:id/monitor" element={<TaskMonitor />} />
            <Route path="settings" element={<Settings />} />
          </Route>
        </Routes>
      </Router>
    </ConfigProvider>
  );
}
