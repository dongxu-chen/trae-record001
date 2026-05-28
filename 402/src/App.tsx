import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { Scanner } from "@/components/Scanner/Scanner";
import { HistoryList } from "@/components/History/HistoryList";
import { SettingsPanel } from "@/components/Settings/SettingsPanel";
import { ManualInput } from "@/components/ManualInput/ManualInput";
import { StatisticsPage } from "@/components/Statistics/StatisticsPage";
import { QRCodePage } from "@/components/QRCode/QRCodePage";

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Scanner />} />
        <Route path="/history" element={<HistoryList />} />
        <Route path="/settings" element={<SettingsPanel />} />
        <Route path="/manual" element={<ManualInput />} />
        <Route path="/statistics" element={<StatisticsPage />} />
        <Route path="/qrcode" element={<QRCodePage />} />
      </Routes>
    </Router>
  );
}
