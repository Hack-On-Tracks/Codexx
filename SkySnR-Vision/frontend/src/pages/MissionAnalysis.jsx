import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import * as ms from '../services/missionService';
import * as is from '../services/incidentService';
import DetectionOverlay from '../components/DetectionOverlay';
import PriorityScore from '../components/PriorityScore';
import TerrainSelector from '../components/TerrainSelector';
import { Badge, DISASTER_LABEL, Empty, ErrorMsg, Field, Loading, Notice, fmt } from '../components/ui';

const BLANK = { mission_name: '', disaster_type: 'flood', terrain_type: 'flood', location_description: '' };

export default function MissionAnalysis() {
  const [cfg, setCfg] = useState(null);
  const [missions, setMissions] = useState(null);
  const [form, setForm] = useState(BLANK);
  const [mission, setMission] = useState(null);
  const [dets, setDets] = useState([]);
  const [selId, setSelId] = useState(null);
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [ok, setOk] = useState('');
  const [urgent, setUrgent] = useState(false);
  const [ovLevel, setOvLevel] = useState('');
  const [ovWhy, setOvWhy] = useState('');
  const [notes, setNotes] = useState('');
  const [createdIncident, setCreatedIncident] = useState(null);

  const refreshMissions = () => ms.listMissions().then(setMissions).catch((e) => setError(e.message));
  useEffect(() => { ms.appConfig().then(setCfg).catch(() => setCfg({ inference_configured: false, person_classes: ['person'] })); refreshMissions(); }, []);
  useEffect(() => () => preview && URL.revokeObjectURL(preview), [preview]);

  const sel = useMemo(() => dets.find((d) => d.id === selId) || null, [dets, selId]);
  useEffect(() => { setUrgent(!!sel?.urgent_flag); setOvLevel(sel?.override?.level || ''); setOvWhy(sel?.override?.justification || ''); setNotes(sel?.review_notes || ''); setCreatedIncident(null); }, [selId]); // eslint-disable-line

  const run = async (key, fn) => { setBusy(key); setError(''); setOk(''); try { return await fn(); } catch (e) { setError(e.message); } finally { setBusy(''); } };
  const replaceDet = (d) => setDets((all) => all.map((x) => (x.id === d.id ? d : x)));

  const openMission = (m) => run('open', async () => {
    const [full, d] = await Promise.all([ms.getMission(m.id), ms.missionDetections(m.id)]);
    setMission(full); setDets(d); setSelId(null); setFile(null); setPreview(null);
  });

  const create = (e) => { e.preventDefault(); run('create', async () => {
    const m = await ms.createMission(form); setMission(m); setDets([]); setSelId(null); setOk('Mission created. Now upload an image.'); await refreshMissions();
  }); };

  const onFile = (f) => { setFile(f || null); setPreview(f ? URL.createObjectURL(f) : null); };

  const analyse = () => run('analyze', async () => {
    const r = await ms.analyze(mission.id, file);
    const [full, d] = await Promise.all([ms.getMission(mission.id), ms.missionDetections(mission.id)]);
    setMission(full); setDets(d); setFile(null); setPreview(null); setOk(r.message + ` ${r.detection_count} detection(s) stored.`); await refreshMissions();
  });

  const recalc = () => run('prio', async () => {
    const d = await ms.setPriority(sel.id, { urgent_flag: urgent, override_level: ovLevel || null, override_justification: ovLevel ? ovWhy : null });
    replaceDet(d); setOk('Priority saved.');
  });
  const review = (decision) => run('review', async () => {
    const d = await ms.reviewDetection(sel.id, { decision, notes }); replaceDet(d); setOk(decision === 'confirmed' ? 'Detection confirmed.' : 'Detection dismissed.');
  });
  const makeIncident = () => run('inc', async () => { const i = await is.createIncident({ detection_id: sel.id, manager_notes: notes }); setCreatedIncident(i); setOk('Incident created.'); });

  const isPerson = (d) => (cfg?.person_classes || ['person']).includes(d.object_class.toLowerCase());
  const analysed = mission?.status === 'analyzed';

  return (
    <div className="stack">
      <h1>Mission analysis</h1>
      {cfg && !cfg.inference_configured && <div className="alert">Inference is not configured on the server, so images cannot be analysed yet. Add <code>ROBOFLOW_API_KEY</code> and <code>ROBOFLOW_MODEL_ID</code> to <code>backend/.env</code>. No fake predictions are shown.</div>}
      <ErrorMsg error={error} /><Notice>{ok}</Notice>

      <div className="grid cols-2">
        <form className="card" onSubmit={create}>
          <h3>1. Create a mission</h3>
          <Field label="Mission name"><input required minLength={3} value={form.mission_name} onChange={(e) => setForm({ ...form, mission_name: e.target.value })} placeholder="e.g. Mumbai Urban Flood Response" /></Field>
          <Field label="Location description"><input value={form.location_description} onChange={(e) => setForm({ ...form, location_description: e.target.value })} placeholder="e.g. Kurla, Mumbai" /></Field>
          <Field label="Disaster type"><select value={form.disaster_type} onChange={(e) => setForm({ ...form, disaster_type: e.target.value })}>
            {Object.entries(DISASTER_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></Field>
          <Field label="Terrain"><TerrainSelector value={form.terrain_type} onChange={(t) => setForm({ ...form, terrain_type: t })} /></Field>
          <button className="btn" disabled={busy === 'create'}>{busy === 'create' ? 'Creating…' : 'Create mission'}</button>
        </form>

        <div className="card stack">
          <h3>Open an existing mission</h3>
          {!missions ? <Loading /> : missions.length === 0 ? <Empty>No missions created yet.</Empty> : (
            <div style={{ maxHeight: 300, overflow: 'auto' }}>{missions.map((m) => (
              <div key={m.id} className={`det-item ${mission?.id === m.id ? 'sel' : ''}`} onClick={() => openMission(m)}>
                <strong>{m.mission_name}</strong><div className="muted">{DISASTER_LABEL[m.disaster_type]} · {fmt(m.created_at)} · <Badge value={m.status === 'analyzed' ? 'confirmed' : 'pending'} label={m.status === 'analyzed' ? 'Analysed' : 'Awaiting image'} /></div></div>))}</div>)}
        </div>
      </div>

      {mission && !analysed && (
        <div className="card stack">
          <h3>2. Upload a drone image — {mission.mission_name}</h3>
          <p className="muted">Images only (JPG, PNG, WebP, up to {cfg?.max_upload_mb || 10} MB). Video analysis is not available.</p>
          <input type="file" accept=".jpg,.jpeg,.png,.webp,image/*" onChange={(e) => onFile(e.target.files[0])} />
          {preview && <img src={preview} alt="Selected upload preview" style={{ maxWidth: 420, borderRadius: 10, border: '1px solid var(--line)' }} />}
          <div><button className="btn" disabled={!file || busy === 'analyze' || (cfg && !cfg.inference_configured)} onClick={analyse}>{busy === 'analyze' ? 'Analysing…' : 'Analyse image'}</button></div>
        </div>
      )}

      {analysed && (
        <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))' }}>
          <div className="card stack">
            <h3>3. Review detections — {mission.mission_name}</h3>
            <p className="muted">These are AI predictions, not confirmed findings. Select a box or a row to review it.</p>
            <DetectionOverlay imageRef={mission.media_reference} width={mission.image_width} height={mission.image_height} detections={dets} selectedId={selId} onSelect={setSelId} personClasses={cfg?.person_classes || ['person']} />
            {dets.length === 0 ? <Empty>No objects were detected in this image.</Empty> : dets.map((d) => (
              <div key={d.id} className={`det-item ${selId === d.id ? 'sel' : ''}`} onClick={() => setSelId(d.id)}>
                <div className="row between"><strong>{d.object_class}</strong><span className="row"><span>{(d.confidence * 100).toFixed(0)}%</span><Badge value={d.review_status} /></span></div>
                <div className="muted">ID {d.id.slice(-6)} · x {Math.round(d.bounding_box.x)}, y {Math.round(d.bounding_box.y)}, {Math.round(d.bounding_box.width)}×{Math.round(d.bounding_box.height)} px</div>
              </div>))}
          </div>

          <div className="card stack">
            {!sel ? <Empty>Select a detection to review it.</Empty> : (<>
              <h3>{sel.object_class} · {(sel.confidence * 100).toFixed(1)}% confidence</h3>
              {isPerson(sel) ? <>
                <PriorityScore score={sel.priority_score} level={sel.priority_level} finalLevel={sel.final_priority_level} breakdown={sel.score_breakdown} explanation={sel.score_explanation} override={sel.override} />
                <label><input type="checkbox" checked={urgent} onChange={(e) => setUrgent(e.target.checked)} /> Mark as urgent (+25)</label>
                <Field label="Override final priority (optional)"><select value={ovLevel} onChange={(e) => setOvLevel(e.target.value)}><option value="">Keep calculated level</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select></Field>
                {ovLevel && <Field label="Reason for override (required)"><input value={ovWhy} onChange={(e) => setOvWhy(e.target.value)} /></Field>}
                <button className="btn secondary" disabled={busy === 'prio' || (ovLevel && !ovWhy.trim())} onClick={recalc}>{busy === 'prio' ? 'Saving…' : 'Recalculate and save priority'}</button>
              </> : <p className="muted">Priority scoring applies to person detections only.</p>}
              <hr style={{ width: '100%', border: 0, borderTop: '1px solid var(--line)' }} />
              <Field label="Verification notes (required to decide)"><textarea value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="What did you see in the image?" /></Field>
              <div className="row">
                <button className="btn" disabled={busy === 'review' || notes.trim().length < 3} onClick={() => review('confirmed')}>Confirm detection</button>
                <button className="btn secondary" disabled={busy === 'review' || notes.trim().length < 3} onClick={() => review('dismissed')}>Dismiss</button>
              </div>
              {sel.review_status === 'confirmed' && !createdIncident && <button className="btn" disabled={busy === 'inc'} onClick={makeIncident}>Create incident from this detection</button>}
              {createdIncident && <Notice>Incident created. <Link to="/manager/incidents">Assign it in Incidents</Link>.</Notice>}
            </>)}
          </div>
        </div>
      )}
    </div>
  );
}
