import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { WorkspacePage } from "@/pages/WorkspacePage";
import { AnnotationPage } from "@/pages/AnnotationPage";
import { StatisticsPage } from "@/pages/StatisticsPage";
import { CollaboratorsPage } from "@/pages/CollaboratorsPage";
import { SettingsPage } from "@/pages/SettingsPage";

export default function App() {
  return (
    <Router>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<WorkspacePage />} />
          <Route path="/collaborators" element={<CollaboratorsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
        <Route path="/project/:id" element={<AnnotationPage />} />
        <Route path="/project/:id/statistics" element={<StatisticsPage />} />
      </Routes>
    </Router>
  );
}
