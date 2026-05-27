import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from '@/components/Layout';
import Home from '@/pages/Home';
import BlockDetail from '@/pages/BlockDetail';
import TransactionDetail from '@/pages/TransactionDetail';
import AddressDetail from '@/pages/AddressDetail';
import ContractDetail from '@/pages/ContractDetail';
import GasTrend from '@/pages/GasTrend';

export default function App() {
  return (
    <Router>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Home />} />
          <Route path="/block/:number" element={<BlockDetail />} />
          <Route path="/tx/:hash" element={<TransactionDetail />} />
          <Route path="/address/:address" element={<AddressDetail />} />
          <Route path="/contract/:address" element={<ContractDetail />} />
          <Route path="/gas" element={<GasTrend />} />
        </Route>
      </Routes>
    </Router>
  );
}
