import { Route, Routes } from 'react-router-dom';
import ProtectedRoute from './auth/ProtectedRoute';
import AppLayout from './components/layout/AppLayout';
import Login from './pages/Login';
import Register from './pages/Register';
import Home from './pages/Home';
import Analyse from './pages/Analyse';
import History from './pages/History';
import DiseaseInfo from './pages/DiseaseInfo';
import DiseaseDetails from './pages/DiseaseDetails';
import NotFound from './pages/NotFound';

export default function App() {
  return (
    <Routes>
      {/* Public */}
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      {/* Protected: every route below requires a backend-verified session */}
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route index element={<Home />} />
          <Route path="/analyse" element={<Analyse />} />
          <Route path="/history" element={<History />} />
          <Route path="/info" element={<DiseaseInfo />} />
          <Route path="/info/:diseaseCode" element={<DiseaseDetails />} />
        </Route>
      </Route>

      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
