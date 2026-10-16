import { Navigate, Route, Routes } from 'react-router-dom';
import { HOME, useAuth } from './context/AuthContext';
import AppLayout from './layouts/AppLayout';
import { Loading } from './components/ui';
import LandingPage from './pages/LandingPage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import AdminDashboard from './pages/AdminDashboard';
import UserApprovals from './pages/UserApprovals';
import ManagerDashboard from './pages/ManagerDashboard';
import MissionAnalysis from './pages/MissionAnalysis';
import MLClassifier from './pages/MLClassifier';
import IncidentManagement from './pages/IncidentManagement';
import Reports from './pages/Reports';
import MemberDashboard from './pages/MemberDashboard';
import AssignedIncidents from './pages/AssignedIncidents';

// UI-level guard only. The backend enforces every permission independently.
function Guard({ role, children }) {
  const { user, loading } = useAuth();
  if (loading) return <Loading />;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== role) return <Navigate to={HOME[user.role]} replace />;
  return children;
}

function PublicOnly({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <Loading />;
  return user ? <Navigate to={HOME[user.role]} replace /> : children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<PublicOnly><LoginPage /></PublicOnly>} />
      <Route path="/register" element={<PublicOnly><RegisterPage /></PublicOnly>} />
      <Route element={<Guard role="admin"><AppLayout /></Guard>}>
        <Route path="/admin" element={<AdminDashboard />} />
        <Route path="/admin/users" element={<UserApprovals />} />
      </Route>
      <Route element={<Guard role="rescue_manager"><AppLayout /></Guard>}>
        <Route path="/manager" element={<ManagerDashboard />} />
        <Route path="/manager/analysis" element={<MissionAnalysis />} />
        <Route path="/manager/ml-classifier" element={<MLClassifier />} />
        <Route path="/manager/incidents" element={<IncidentManagement />} />
        <Route path="/manager/reports" element={<Reports />} />
      </Route>
      <Route element={<Guard role="rescue_member"><AppLayout /></Guard>}>
        <Route path="/member" element={<MemberDashboard />} />
        <Route path="/member/incidents" element={<AssignedIncidents />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
