import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Home from "@/pages/Home";
import ShareAccess from "@/pages/ShareAccess";

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/share/:shareId" element={<ShareAccess />} />
      </Routes>
    </Router>
  );
}
