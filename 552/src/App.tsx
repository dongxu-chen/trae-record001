import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Layout from "@/components/Layout/Layout";
import HomePage from "@/pages/HomePage";
import VerifyResultPage from "@/pages/VerifyResultPage";
import HistoryPage from "@/pages/HistoryPage";
import HelpPage from "@/pages/HelpPage";
import NotFoundPage from "@/pages/NotFoundPage";

export default function App() {
  return (
    <Router>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/verify/:id" element={<VerifyResultPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/help" element={<HelpPage />} />
        </Route>
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Router>
  );
}
