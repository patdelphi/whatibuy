import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { DashboardLayout } from './layouts/DashboardLayout';
import { Analysis } from './pages/Analysis';
import { Orders } from './pages/Orders';
import './index.css';

function App() {
  return (
    <Router>
      <DashboardLayout>
        <Routes>
          <Route path="/" element={<Analysis />} />
          <Route path="/orders" element={<Orders />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </DashboardLayout>
    </Router>
  );
}

export default App;
