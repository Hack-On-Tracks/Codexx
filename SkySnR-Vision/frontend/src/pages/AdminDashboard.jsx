import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import * as auth from '../services/authService';
import { Badge, Empty, ErrorMsg, Loading, ROLE_SHORT, fmt } from '../components/ui';

export default function AdminDashboard() {
  const [stats, setStats] = useState(null);
  const [pending, setPending] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => {
    Promise.all([auth.stats(), auth.listUsers('pending')]).then(([s, p]) => { setStats(s); setPending(p); }).catch((e) => setError(e.message));
  }, []);
  if (error) return <ErrorMsg error={error} />;
  if (!stats) return <Loading />;
  const cards = [['Rescue Operations Managers', stats.total_managers, '/admin/users?role=rescue_manager'], ['Rescue Team Members', stats.total_members, '/admin/users?role=rescue_member'],
    ['Pending approvals', stats.pending_approvals, '/admin/users?status=pending'], ['Approved accounts', stats.approved_accounts, '/admin/users?status=approved']];
  return (
    <div className="stack">
      <h1>Admin dashboard</h1>
      <div className="grid cols-4">{cards.map(([l, n, to]) => <Link key={l} to={to} className="card metric"><div className="n">{n}</div><div>{l}</div></Link>)}</div>
      <div className="card"><div className="row between"><h3>Pending requests</h3><Link to="/admin/users?status=pending">Review all</Link></div>
        {pending.length === 0 ? <Empty>No pending requests.</Empty> : (
          <div className="table-wrap"><table><thead><tr><th>Name</th><th>Role</th><th>Requested</th></tr></thead><tbody>
            {pending.slice(0, 5).map((u) => <tr key={u.id}><td>{u.full_name}</td><td>{ROLE_SHORT[u.role]}</td><td>{fmt(u.created_at)}</td></tr>)}</tbody></table></div>)}
      </div>
    </div>
  );
}
