import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Header from './components/Header';
import UploadPage from './pages/UploadPage';
import ConfigurePage from './pages/ConfigurePage';
import ResultsPage from './pages/ResultsPage';

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <Header />
        <Routes>
          <Route path="/" element={<UploadPage />} />
          <Route path="/configure" element={<ConfigurePage />} />
          <Route path="/results" element={<ResultsPage />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;
