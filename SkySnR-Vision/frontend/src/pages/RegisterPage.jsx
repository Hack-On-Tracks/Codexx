import { useState } from 'react';
import { Link } from 'react-router-dom';
import * as auth from '../services/authService';
import { ErrorMsg, Field, Notice } from '../components/ui';

export default function RegisterPage() {
  const [f, setF] = useState({ full_name: '', email: '', password: '', confirm_password: '', role: 'rescue_member' });
  const [error, setError] = useState('');
  const [done, setDone] = useState('');
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  async function submit(e) {
    e.preventDefault(); setError('');
    if (f.full_name.trim().length < 2) return setError('Enter your full name.');
    if (!f.email.includes('@')) return setError('Enter a valid email address.');
    if (f.password.length < 8) return setError('Password must be at least 8 characters.');
    if (f.password !== f.confirm_password) return setError('Passwords do not match.');
    setBusy(true);
    try { const r = await auth.register(f); setDone(r.message); }
    catch (err) { setError(err.message); } finally { setBusy(false); }
  }

  if (done) return (
    <div className="auth-wrap"><div className="card stack"><h2>Request received</h2><Notice>{done}</Notice>
      <p className="muted">You cannot sign in until an admin approves your account.</p><Link to="/login" className="btn">Back to sign in</Link></div></div>
  );

  return (
    <div className="auth-wrap">
      <Link to="/" className="muted">← SkySnR Vision</Link>
      <div className="card" style={{ marginTop: '1rem' }}>
        <h2>Request an account</h2>
        <ErrorMsg error={error} />
        <form onSubmit={submit} noValidate>
          <Field label="Full name"><input value={f.full_name} onChange={set('full_name')} /></Field>
          <Field label="Email"><input type="email" value={f.email} onChange={set('email')} autoComplete="username" /></Field>
          <Field label="Role">
            <select value={f.role} onChange={set('role')}>
              <option value="rescue_member">Rescue Team Member</option>
              <option value="rescue_manager">Rescue Operations Manager</option>
            </select>
          </Field>
          <Field label="Password (8+ characters)"><input type="password" value={f.password} onChange={set('password')} autoComplete="new-password" /></Field>
          <Field label="Confirm password"><input type="password" value={f.confirm_password} onChange={set('confirm_password')} autoComplete="new-password" /></Field>
          <button className="btn" disabled={busy} style={{ width: '100%' }}>{busy ? 'Submitting…' : 'Submit request'}</button>
        </form>
        <p className="muted" style={{ marginTop: '1rem' }}>Already approved? <Link to="/login">Sign in</Link></p>
      </div>
    </div>
  );
}
