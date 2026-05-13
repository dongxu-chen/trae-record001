import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Record from './pages/Record';
import Edit from './pages/Edit';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Record />} />
        <Route path="/edit/:id" element={<Edit />} />
      </Routes>
    </Router>
  );
}

export default App;