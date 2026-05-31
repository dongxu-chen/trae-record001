import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Navbar from "@/components/Navbar";
import Home from "@/pages/Home";
import SearchResults from "@/pages/SearchResults";
import ProductDetail from "@/pages/ProductDetail";
import HotDrops from "@/pages/HotDrops";
import Coupons from "@/pages/Coupons";
import Favorites from "@/pages/Favorites";
import Alerts from "@/pages/Alerts";

export default function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <main className="pt-0">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/search" element={<SearchResults />} />
            <Route path="/product/:id" element={<ProductDetail />} />
            <Route path="/products/hot" element={<HotDrops />} />
            <Route path="/products/coupons" element={<Coupons />} />
            <Route path="/user/favorites" element={<Favorites />} />
            <Route path="/user/alerts" element={<Alerts />} />
            <Route
              path="*"
              element={
                <div className="flex flex-col items-center justify-center py-20 text-center">
                  <h1 className="text-4xl font-bold text-gray-900 mb-4">404</h1>
                  <p className="text-gray-600 mb-6">页面不存在或已被移除</p>
                  <button
                    onClick={() => (window.location.href = "/")}
                    className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    返回首页
                  </button>
                </div>
              }
            />
          </Routes>
        </main>
      </div>
    </Router>
  );
}
