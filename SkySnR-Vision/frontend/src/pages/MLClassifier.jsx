import { useEffect, useState } from 'react';
import { request } from '../services/api';

export default function MLClassifier() {
  const [file, setFile] = useState(null); const [preview, setPreview] = useState('');
  const [status, setStatus] = useState(null); const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false); const [error, setError] = useState('');
  useEffect(() => { request('/ml/status').then(setStatus).catch(e => setError(e.message)); }, []);
  function choose(f) { setFile(f || null); setResult(null); setError(''); if (preview) URL.revokeObjectURL(preview); setPreview(f ? URL.createObjectURL(f) : ''); }
  async function classify(e) { e.preventDefault(); if (!file) return; setBusy(true); setError(''); setResult(null); try { const form = new FormData(); form.append('file', file); setResult(await request('/ml/classify', { method: 'POST', form })); } catch (e) { setError(e.message); } finally { setBusy(false); } }
  return <section className="stack"><div><p className="eyebrow">LOCAL MACHINE LEARNING</p><h1>AIDER disaster image classifier</h1><p className="muted">Upload an image to run inference through the Keras model packaged with this project.</p></div>
    <div className="card stack"><div className="row between"><h3>Model connection</h3><span className={`badge ${status?.configured ? 'success' : ''}`}>{status?.configured ? 'Model files found' : 'Checking model…'}</span></div>
    {status && <p className="muted">Task: image classification · Classes: {status.classes.join(', ')}</p>}
    <p className="muted">This classifier predicts <strong>Collapsed Building/Rubble</strong>, <strong>Fire/Smoke</strong>, or <strong>Normal</strong>. It does not produce object boxes or person/vehicle detections.</p></div>
    <form className="card stack" onSubmit={classify}><h3>Test an image</h3><input type="file" accept="image/jpeg,image/png,image/webp" onChange={e => choose(e.target.files?.[0])} required />
    {preview && <img src={preview} alt="Selected image preview" style={{maxWidth: 'min(100%, 520px)', maxHeight: 360, objectFit: 'contain', borderRadius: 12}} />}
    <div><button className="btn" disabled={!file || busy || status?.configured === false}>{busy ? 'Running model…' : 'Classify image'}</button></div>
    {error && <div className="notice error">{error}</div>}
    {result && <div className="stack"><h3>Prediction: {result.prediction.label}</h3><p>Confidence: {(result.prediction.confidence * 100).toFixed(2)}%</p>{result.probabilities.map(p => <div key={p.label} className="stack" style={{gap: 4}}><div className="row between"><span>{p.label}</span><strong>{(p.confidence * 100).toFixed(2)}%</strong></div><div style={{height: 8, background: 'var(--line)', borderRadius: 20, overflow: 'hidden'}}><div style={{height: '100%', width: `${Math.max(0,Math.min(100,p.confidence*100))}%`, background: 'var(--brand, #26785b)'}} /></div></div>)}<p className="muted">{result.note}</p></div>}</form></section>;
}
