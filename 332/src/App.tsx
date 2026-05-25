import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { ToastProvider, GlobalToastListener } from "@/components/ui/toast";
import Navbar from "@/components/Navbar";
import Generator from "@/pages/Generator";
import BatchGenerate from "@/pages/BatchGenerate";
import DynamicCode from "@/pages/DynamicCode";
import Statistics from "@/pages/Statistics";
import MyQRCodes from "@/pages/MyQRCodes";
import ArtQRCode from "@/pages/ArtQRCode";
import LandingAnalysis from "@/pages/LandingAnalysis";
import Management from "@/pages/Management";

export default function App() {
  return (
    <ToastProvider>
      <GlobalToastListener />
      <Router>
        <div className="min-h-screen bg-slate-950">
          <Navbar />
          <Routes>
            <Route path="/" element={<Generator />} />
            <Route path="/batch" element={<BatchGenerate />} />
            <Route path="/dynamic" element={<DynamicCode />} />
            <Route path="/statistics" element={<Statistics />} />
            <Route path="/my-codes" element={<MyQRCodes />} />
            <Route path="/art" element={<ArtQRCode />} />
            <Route path="/analysis" element={<LandingAnalysis />} />
            <Route path="/management" element={<Management />} />
          </Routes>
        </div>
      </Router>
    </ToastProvider>
  );
}
