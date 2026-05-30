import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import MainLayout from "@/components/layout/MainLayout";
import Dashboard from "@/pages/Dashboard";
import VersionList from "@/pages/VersionList";
import VersionDetail from "@/pages/VersionDetail";
import SwaggerDocs from "@/pages/SwaggerDocs";
import ClientGuide from "@/pages/ClientGuide";
import Routing from "@/pages/Routing";
import Compare from "@/pages/Compare";

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route element={<MainLayout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/versions" element={<VersionList />} />
          <Route path="/versions/:id" element={<VersionDetail />} />
          <Route path="/route" element={<Routing />} />
          <Route path="/compare" element={<Compare />} />
          <Route path="/swagger" element={<SwaggerDocs />} />
          <Route path="/guide" element={<ClientGuide />} />
        </Route>
      </Routes>
    </Router>
  );
}
