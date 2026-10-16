import { useCallback, useEffect, useState } from 'react';
import * as is from '../services/incidentService';
import { mediaUrl } from '../services/api';
import { Badge, Empty, ErrorMsg, Field, Loading, Notice, Tabs, TERRAIN_LABEL, Timeline, fmt } from '../components/ui';

function IncidentCard({ inc, onChanged, onError, onOk }) {
  const [open, setOpen] = useState(false);
  const [events, setEvents] = useState([]);
  const [note, setNote] = useState('');
  const [outcome, setOutcome] = useState('');
  const [obs, setObs] = useState('');
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);

  const loadEvents = useCallback(() => is.events(inc.id).then(setEvents).catch((e) => onError(e.message)), [inc.id, onError]);
  useEffect(() => { if (open) loadEvents(); }, [open, loadEvents]);

  async function act(fn, msg) {
    setBusy(true); onError(''); onOk('');
    try { await fn(); onOk(msg); await onChanged(); if (open) await loadEvents(); } catch (e) { onError(e.message); } finally { setBusy(false); }
  }
  const stage = inc.status === 'assigned' && !inc.acknowledged_at ? 'new' : inc.status;

  return (
    <div className="card stack">
      <div className="row between"><h3>Incident {inc.id.slice(-6)}</h3><span className="row"><Badge value={inc.priority_level} /><Badge value={inc.status} label={stage === 'new' ? 'New assignment' : undefined} /></span></div>
      <p className="muted">{TERRAIN_LABEL[inc.terrain_type]} · assigned {fmt(inc.assigned_at)}{inc.acknowledged_at && ` · acknowledged ${fmt(inc.acknowledged_at)}`}</p>
      {inc.manager_notes && <p><strong>Manager notes:</strong> {inc.manager_notes}</p>}
      <div className="row">
        {stage === 'new' && <button className="btn" disabled={busy} onClick={() => act(() => is.acknowledge(inc.id), 'Assignment acknowledged.')}>Acknowledge assignment</button>}
        {inc.status === 'assigned' && inc.acknowledged_at && <button className="btn" disabled={busy} onClick={() => act(() => is.start(inc.id), 'Response started.')}>Start response</button>}
        <button className="btn secondary" onClick={() => setOpen(!open)}>{open ? 'Hide details' : 'Details and updates'}</button>
      </div>
      {open && (<>
        <IncidentEvidence id={inc.id} />
        <h4>Timeline</h4><Timeline events={events} />
        {inc.status !== 'resolved' && (<>
          <Field label="Add a rescue note"><textarea value={note} onChange={(e) => setNote(e.target.value)} /></Field>
          <div><button className="btn secondary sm" disabled={busy || note.trim().length < 2} onClick={() => act(async () => { await is.addNote(inc.id, note); setNote(''); }, 'Note saved.')}>Save note</button></div></>)}
        {inc.status === 'in_progress' && (
          <div className="card stack"><h4>Mark resolved</h4>
            <Field label="Outcome description (required)"><textarea value={outcome} onChange={(e) => setOutcome(e.target.value)} /></Field>
            <Field label="Field observations"><textarea value={obs} onChange={(e) => setObs(e.target.value)} /></Field>
            <Field label="Supporting evidence image (optional)"><input type="file" accept="image/*" onChange={(e) => setFile(e.target.files[0] || null)} /></Field>
            <div><button className="btn" disabled={busy || outcome.trim().length < 3} onClick={() => act(() => is.resolve(inc.id, { outcome, field_observations: obs, file }), 'Incident resolved.')}>Mark resolved</button></div>
          </div>)}
        {inc.status === 'resolved' && <div className="alert ok"><strong>Outcome:</strong> {inc.outcome}{inc.field_observations && <><br /><strong>Observations:</strong> {inc.field_observations}</>}</div>}
      </>)}
    </div>
  );
}

function IncidentEvidence({ id }) {
  const [d, setD] = useState(null);
  useEffect(() => { is.getIncident(id).then(setD).catch(() => setD(false)); }, [id]);
  if (d === null) return <Loading />;
  if (!d) return <p className="muted">Evidence could not be loaded.</p>;
  return (<div className="stack">
    <p className="muted">{d.mission.mission_name} · {d.mission.location_description || 'Location not recorded'}</p>
    {d.evidence_url ? <img src={mediaUrl(d.detection.frame_or_image_reference)} alt="Evidence from the drone image" style={{ width: '100%', borderRadius: 10, border: '1px solid var(--line)' }} /> : <p className="muted">No evidence image.</p>}
    <p className="muted">Priority {d.priority_score}/100 ({d.priority_level}). {d.explanation}</p></div>);
}

export default function AssignedIncidents() {
  const [status, setStatus] = useState('');
  const [list, setList] = useState(null);
  const [error, setError] = useState('');
  const [ok, setOk] = useState('');
  const load = useCallback(() => is.listIncidents({ status }).then(setList).catch((e) => setError(e.message)), [status]);
  useEffect(() => { setList(null); load(); }, [load]);
  return (
    <div className="stack">
      <h1>My assigned incidents</h1>
      <Tabs value={status} onChange={setStatus} options={[['', 'All'], ['assigned', 'Assigned'], ['in_progress', 'In progress'], ['resolved', 'Resolved']]} />
      <ErrorMsg error={error} /><Notice>{ok}</Notice>
      {!list ? <Loading /> : list.length === 0 ? <Empty>No incidents here.</Empty> : list.map((i) => <IncidentCard key={i.id} inc={i} onChanged={load} onError={setError} onOk={setOk} />)}
    </div>
  );
}
