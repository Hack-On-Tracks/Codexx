import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { ROLE_LABEL, useAuth } from '../context/AuthContext';

const NAV = {
  admin: [['/admin', 'Dashboard', true], ['/admin/users', 'User approvals']],
  rescue_manager: [['/manager', 'Dashboard', true], ['/manager/analysis', 'Mission analysis'], ['/manager/ml-classifier', 'AIDER image classifier'], ['/manager/incidents', 'Incidents'], ['/manager/reports', 'Reports']],
  rescue_member: [['/member', 'Dashboard', true], ['/member/incidents', 'My incidents']],
};

export default function AppLayout() {
  const { user, signOut } = useAuth();
  const nav = useNavigate();
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">SkySnR Vision</div>
        <nav aria-label="Main">{NAV[user.role].map(([to, label, end]) => <NavLink key={to} to={to} end={end}>{label}</NavLink>)}</nav>
        <div className="who"><strong>{user.full_name}</strong><br />{ROLE_LABEL[user.role]}</div>
        <button className="btn" onClick={async () => { await signOut(); nav('/login'); }}>Sign out</button>
      </aside>
      <main className="main"><Outlet /></main>
    </div>
  );
}
