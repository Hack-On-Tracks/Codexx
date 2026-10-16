import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import * as auth from '../services/authService';
import * as is from '../services/incidentService';
import { Badge, Empty, ErrorMsg, Loading, fmt } from '../components/ui';

export default function MemberDashboard() {
  const [d, setD] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => { Promise.all([auth.stats(), is.listIncidents()]).then(([stats, list]) => setD({ stats, list })).catch((e) => setError(e.message)); }, []);
  if (error) return <ErrorMsg error={error} />;
  if (!d) return <Loading />;
  const { stats: s, list } = d;
  const todo = list.filter((i) => i.status !== 'resolved');
  const cards = [['Assigned to me', s.assigned_total], ['Awaiting my acknowledgement', s.awaiting_acknowledgement], ['In progress', s.in_progress], ['Resolved', s.resolved]];
  const recent = [...list].sort((a, b) => (b.updated_at || '').localeCompare(a.updated_at || '')).slice(0, 5);
  return (
    <div className="stack">
      <h1>My dashboard</h1>
      <div className="grid cols-4">{cards.map(([l, n]) => <Link to="/member/incidents" key={l} className="card metric"><div className="n">{n}</div><div>{l}</div></Link>)}</div>
      <div className="grid cols-2">
        <div className="card"><h3>Needs action</h3>
          {todo.length === 0 ? <Empty>Nothing assigned to you right now.</Empty> : todo.map((i) => (
            <Link key={i.id} to="/member/incidents" className="row between" style={{ padding: '.4rem 0', borderBottom: '1px solid var(--line)', color: 'inherit' }}>
              <span>Incident {i.id.slice(-6)}</span><span className="row"><Badge value={i.priority_level} /><Badge value={i.status} label={i.status === 'assigned' && !i.acknowledged_at ? 'New' : undefined} /></span></Link>))}
        </div>
        <div className="card"><h3>Recent updates</h3>
          {recent.length === 0 ? <Empty>No updates yet.</Empty> : recent.map((i) => <div key={i.id} className="row between" style={{ padding: '.4rem 0', borderBottom: '1px solid var(--line)' }}><span>Incident {i.id.slice(-6)}</span><span className="muted">{fmt(i.updated_at)}</span></div>)}
        </div>
      </div>
    </div>
  );
}
