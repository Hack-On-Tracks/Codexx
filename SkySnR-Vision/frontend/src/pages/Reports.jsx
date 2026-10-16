import { useEffect, useState } from 'react';
import * as rs from '../services/reportService';
import * as ms from '../services/missionService';
import * as is from '../services/incidentService';
import { downloadUrl } from '../services/api';
import { Badge, Empty, ErrorMsg, Field, Loading, Notice, fmt } from '../components/ui';

export default function Reports() {
  const [missions, setMissions] = useState(null);
  const [reports, setReports] = useState(null);
  const [missionId, setMissionId] = useState('');
  const [incidents, setIncidents] = useState([]);
  const [incidentId, setIncidentId] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [ok, setOk] = useState('');

  const load = () => Promise.all([ms.listMissions(), rs.listReports()]).then(([m, r]) => { setMissions(m); setReports(r); }).catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);
  useEffect(() => { setIncidentId(''); setIncidents([]); if (missionId) is.listIncidents({ mission_id: missionId }).then(setIncidents).catch((e) => setError(e.message)); }, [missionId]);

  async function generate() {
    setBusy(true); setError(''); setOk('');
    try { const r = await rs.generate(missionId, incidentId); setOk('Report generated.'); setReports((x) => [r, ...(x || [])]); }
    catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  const nameOf = (id) => missions?.find((m) => m.id === id)?.mission_name || 'Unknown mission';

  return (
    <div className="stack">
      <h1>Evidence reports</h1>
      <ErrorMsg error={error} /><Notice>{ok}</Notice>
      <div className="card">
        <h3>Generate a report</h3>
        <p className="muted">Reports are built on the server from saved records only. AI predictions and manager-confirmed findings are labelled separately.</p>
        {!missions ? <Loading /> : missions.length === 0 ? <Empty>No missions yet.</Empty> : (<>
          <Field label="Mission"><select value={missionId} onChange={(e) => setMissionId(e.target.value)}><option value="">Choose a mission…</option>
            {missions.map((m) => <option key={m.id} value={m.id}>{m.mission_name} ({fmt(m.created_at)})</option>)}</select></Field>
          {missionId && <Field label="Scope"><select value={incidentId} onChange={(e) => setIncidentId(e.target.value)}><option value="">Whole mission (all incidents)</option>
            {incidents.map((i) => <option key={i.id} value={i.id}>Incident {i.id.slice(-6)} — {i.status}</option>)}</select></Field>}
          <button className="btn" disabled={!missionId || busy} onClick={generate}>{busy ? 'Generating…' : 'Generate PDF'}</button></>)}
      </div>
      <div className="card"><h3>Generated reports</h3>
        {!reports ? <Loading /> : reports.length === 0 ? <Empty>No reports generated yet.</Empty> : (
          <div className="table-wrap"><table><thead><tr><th>Mission</th><th>Generated</th><th>Status</th><th /></tr></thead><tbody>
            {reports.map((r) => <tr key={r.id}><td>{nameOf(r.mission_id)}</td><td>{fmt(r.generated_at)}</td><td><Badge value={r.status === 'ready' ? 'approved' : 'pending'} label={r.status === 'ready' ? 'Ready' : 'Not ready'} /></td>
              <td>{r.status === 'ready' && <a className="btn sm" href={downloadUrl(r.id)}>Download PDF</a>}</td></tr>)}</tbody></table></div>)}
      </div>
    </div>
  );
}
