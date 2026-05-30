import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { ShaderProvider } from "@/contexts/ShaderContext";
import Home from "@/pages/Home";

export default function App() {
  return (
    <ShaderProvider>
      <Router>
        <Routes>
          <Route path="/" element={<Home />} />
        </Routes>
      </Router>
    </ShaderProvider>
  );
}
