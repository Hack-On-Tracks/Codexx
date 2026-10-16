import { useEffect } from 'react';

export const STATUS_LABEL = {
  pending_assignment: 'Awaiting assignment', assigned: 'Assigned', in_progress: 'In progress', resolved: 'Resolved',
  pending: 'Pending', approved: 'Approved', rejected: 'Rejected', unreviewed: 'Awaiting review', confirmed: 'Confirmed', dismissed: 'Dismissed',
  high: 'High', medium: 'Medium', low: 'Low',
};
export const DISASTER_LABEL = { flood: 'Flood', fire: 'Fire', earthquake_building_collapse: 'Earthquake / building collapse', landslide: 'Landslide' };
export const TERRAIN_LABEL = { flood: 'Flood', urban_earthquake: 'Urban / Earthquake', forest: 'Forest', mountain: 'Mountain' };

export const Badge = ({ value, label }) => <span className={`badge ${value}`}>{label || STATUS_LABEL[value] || value}</span>;
export const Loading = () => <div className="spinner" role="status" aria-label="Loading" />;
export const ErrorMsg = ({ error }) => (error ? <div className="alert" role="alert">{error}</div> : null);
export const Notice = ({ children }) => (children ? <div className="alert ok" role="status">{children}</div> : null);
export const Empty = ({ children }) => <div className="empty">{children}</div>;
export const fmt = (iso) => (iso ? new Date(iso).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' }) : 'Not recorded');

export function Field({ label, error, children }) {
  return <div className="field"><label>{label}</label>{children}{error && <div className="err">{error}</div>}</div>;
}

export function Modal({ title, onClose, children }) {
  useEffect(() => { const k = (e) => e.key === 'Escape' && onClose(); window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k); }, [onClose]);
  return (
    <div className="modal-bg" onClick={onClose}>
      <div className="modal" role="dialog" aria-modal="true" aria-label={title} onClick={(e) => e.stopPropagation()}>
        <div className="row between"><h3>{title}</h3><button className="btn sm secondary" onClick={onClose}>Close</button></div>
        {children}
      </div>
    </div>
  );
}

export function Timeline({ events }) {
  if (!events?.length) return <Empty>No activity recorded yet.</Empty>;
  return (
    <ul className="timeline">
      {events.map((e) => (
        <li key={e.id}><strong>{e.event_type.replace(/_/g, ' ')}</strong> <span className="muted">· {e.performed_by_name} · {fmt(e.timestamp)}</span>
          {e.notes && <div>{e.notes}</div>}</li>
      ))}
    </ul>
  );
}

export function Tabs({ options, value, onChange }) {
  return <div className="tabs" role="tablist">{options.map(([v, l]) => <button key={v || 'all'} role="tab" aria-selected={value === v} className={`tab ${value === v ? 'on' : ''}`} onClick={() => onChange(v)}>{l}</button>)}</div>;
}

export const ROLE_SHORT = { admin: 'Admin', rescue_manager: 'Manager', rescue_member: 'Team member' };
