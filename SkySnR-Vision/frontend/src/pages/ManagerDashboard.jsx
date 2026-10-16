import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import * as auth from '../services/authService';
import * as inc from '../services/incidentService';
import { Badge, Empty, ErrorMsg, Loading, fmt } from '../components/ui';

export default function ManagerDashboard() {
  const [d, setD] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => {
    Promise.all([auth.stats(), inc.listIncidents(), inc.team()]).then(([stats, incidents, team]) => setD({ stats, incidents, team })).catch((e) => setError(e.message));
  }, []);
  if (error) return <ErrorMsg error={error} />;
  if (!d) return <Loading />;
  const { stats: s, incidents, team } = d;
  const cards = [['Missions', s.total_missions, '/manager/analysis'], ['Detections awaiting review', s.detections_awaiting_review, '/manager/analysis'],
    ['Awaiting assignment', s.pending_assignment, '/manager/incidents?status=pending_assignment'], ['In progress', s.in_progress, '/manager/incidents?status=in_progress'],
    ['Resolved', s.resolved, '/manager/incidents?status=resolved'], ['High priority', s.high, '/manager/incidents?priority=high'],
    ['Medium priority', s.medium, '/manager/incidents?priority=medium'], ['Low priority', s.low, '/manager/incidents?priority=low']];
  const nameOf = Object.fromEntries(team.map((t) => [t.id, t.full_name]));
  return (
    <div className="stack">
      <h1>Manager dashboard</h1>
      <div className="grid cols-4">{cards.map(([l, n, to]) => <Link key={l} to={to} className="card metric"><div className="n">{n}</div><div>{l}</div></Link>)}</div>
      {s.total_missions === 0 && <Empty>No missions created yet. <Link to="/manager/analysis">Create the first mission</Link>.</Empty>}
      <div className="grid cols-2">
        <div className="card"><div className="row between"><h3>Recent incidents</h3><Link to="/manager/incidents">All incidents</Link></div>
          {incidents.length === 0 ? <Empty>No incidents yet.</Empty> : incidents.slice(0, 6).map((i) => (
            <div key={i.id} className="row between" style={{ padding: '.4rem 0', borderBottom: '1px solid var(--line)' }}>
              <span>{fmt(i.created_at)}</span><span className="row"><Badge value={i.priority_level} /><Badge value={i.status} /></span></div>))}
        </div>
        <div className="card"><h3>Team progress</h3>
          {team.length === 0 ? <Empty>No approved team members yet.</Empty> : team.map((t) => (
            <div key={t.id} className="row between" style={{ padding: '.4rem 0', borderBottom: '1px solid var(--line)' }}>
              <span><strong>{t.full_name}</strong></span><span className="muted">{t.open_assignments} open · {t.assigned_total} total</span></div>))}
          <p className="caption">Counts come from saved assignments. Availability is not tracked.</p>
        </div>
      </div>
    </div>
  );
}
