import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import * as is from '../services/incidentService';
import DetectionOverlay from '../components/DetectionOverlay';
import PriorityScore from '../components/PriorityScore';
import { Badge, Empty, ErrorMsg, Field, Loading, Notice, Tabs, TERRAIN_LABEL, Timeline, fmt } from '../components/ui';

export default function IncidentManagement() {
  const [params, setParams] = useSearchParams();
  const status = params.get('status') || '';
  const priority = params.get('priority') || '';
  const [list, setList] = useState(null);
  const [team, setTeam] = useState([]);
  const [selId, setSelId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [events, setEvents] = useState([]);
  const [error, setError] = useState('');
  const [ok, setOk] = useState('');
  const [busy, setBusy] = useState(false);
  const [member, setMember] = useState('');
  const [notes, setNotes] = useState('');
  const [note, setNote] = useState('');

  const loadList = useCallback(() => is.listIncidents({ status, priority_level: priority }).then(setList).catch((e) => setError(e.message)), [status, priority]);
  useEffect(() => { setList(null); loadList(); }, [loadList]);
  useEffect(() => { is.team().then(setTeam).catch((e) => setError(e.message)); }, []);

  const loadDetail = useCallback(async (id) => {
    const [d, ev] = await Promise.all([is.getIncident(id), is.events(id)]);
    setDetail(d); setEvents(ev); setNotes(d.manager_notes || ''); setMember(d.assigned_member?.id || '');
  }, []);
  useEffect(() => { if (selId) { setDetail(null); loadDetail(selId).catch((e) => setError(e.message)); } }, [selId, loadDetail]);

  const act = async (fn, msg) => {
    setBusy(true); setError(''); setOk('');
    try { await fn(); setOk(msg); await Promise.all([loadDetail(selId), loadList(), is.team().then(setTeam)]); }
    catch (e) { setError(e.message); } finally { setBusy(false); }
  };
  const canAssign = detail && (detail.status === 'pending_assignment' || (detail.status === 'assigned' && !detail.acknowledged_at));

  return (
    <div className="stack">
      <h1>Incident management</h1>
      <Tabs value={status} onChange={(v) => setParams({ ...(v && { status: v }), ...(priority && { priority }) })}
        options={[['', 'All'], ['pending_assignment', 'Awaiting assignment'], ['assigned', 'Assigned'], ['in_progress', 'In progress'], ['resolved', 'Resolved']]} />
      <Tabs value={priority} onChange={(v) => setParams({ ...(v && { priority: v }), ...(status && { status }) })}
        options={[['', 'Any priority'], ['high', 'High'], ['medium', 'Medium'], ['low', 'Low']]} />
      <ErrorMsg error={error} /><Notice>{ok}</Notice>
      <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))' }}>
        <div className="card">
          {!list ? <Loading /> : list.length === 0 ? <Empty>No incidents match. Confirm a detection in Mission analysis to create one.</Empty> : list.map((i) => (
            <div key={i.id} className={`det-item ${selId === i.id ? 'sel' : ''}`} onClick={() => setSelId(i.id)}>
              <div className="row between"><strong>Incident {i.id.slice(-6)}</strong><Badge value={i.priority_level} /></div>
              <div className="row between"><span className="muted">{fmt(i.created_at)}</span><Badge value={i.status} /></div>
            </div>))}
        </div>

        <div className="card stack">
          {!selId ? <Empty>Select an incident to see its evidence and timeline.</Empty> : !detail ? <Loading /> : (<>
            <div className="row between"><h3>Incident {detail.id.slice(-6)}</h3><Badge value={detail.status} /></div>
            <p className="muted">{detail.mission.mission_name} · {TERRAIN_LABEL[detail.terrain_type]} · {detail.mission.location_description || 'Location not recorded'}</p>
            {detail.detection && <DetectionOverlay imageRef={detail.detection.frame_or_image_reference} width={detail.detection.image_width} height={detail.detection.image_height} detections={[detail.detection]} selectedId={detail.detection.id} />}
            <PriorityScore score={detail.priority_score} level={detail.priority_level} finalLevel={detail.final_priority_level} explanation={detail.explanation}
              breakdown={detail.detection?.score_breakdown} override={detail.detection?.override} />
            <Field label="Manager notes"><textarea value={notes} onChange={(e) => setNotes(e.target.value)} /></Field>
            <div><button className="btn secondary sm" disabled={busy} onClick={() => act(() => is.updateNotes(detail.id, notes), 'Notes saved.')}>Save notes</button></div>

            <Field label={detail.assigned_member ? `Assigned to ${detail.assigned_member.full_name}` : 'Assign a team member'}>
              <select value={member} onChange={(e) => setMember(e.target.value)} disabled={!canAssign}>
                <option value="">Choose a member…</option>
                {team.map((t) => <option key={t.id} value={t.id}>{t.full_name} — {t.open_assignments} open</option>)}
              </select>
            </Field>
            {team.length === 0 && <p className="muted">No approved, active team members available.</p>}
            <div><button className="btn" disabled={busy || !member || !canAssign} onClick={() => act(() => is.assign(detail.id, member), 'Assignment saved.')}>{detail.assigned_member ? 'Reassign' : 'Assign'}</button>
              {!canAssign && <span className="muted"> Assignment is locked once the member has acknowledged.</span>}</div>

            {detail.status === 'resolved' && <div className="alert ok"><strong>Outcome:</strong> {detail.outcome}{detail.field_observations && <><br /><strong>Field observations:</strong> {detail.field_observations}</>}</div>}
            <h3>Timeline</h3><Timeline events={events} />
            <Field label="Add a note to the timeline"><input value={note} onChange={(e) => setNote(e.target.value)} /></Field>
            <div><button className="btn secondary sm" disabled={busy || note.trim().length < 2} onClick={() => act(async () => { await is.addNote(detail.id, note); setNote(''); }, 'Note added.')}>Add note</button></div>
          </>)}
        </div>
      </div>
    </div>
  );
}
