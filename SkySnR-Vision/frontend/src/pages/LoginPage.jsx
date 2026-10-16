import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { HOME, useAuth } from '../context/AuthContext';
import { ErrorMsg, Field } from '../components/ui';

export default function LoginPage() {
  const { signIn } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [show, setShow] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault(); setError('');
    if (!email.includes('@')) return setError('Enter a valid email address.');
    if (!password) return setError('Enter your password.');
    setBusy(true);
    try { const u = await signIn(email.trim(), password); nav(HOME[u.role], { replace: true }); }
    catch (err) { setError(err.message); } finally { setBusy(false); }
  }

  return (
    <div className="auth-wrap">
      <Link to="/" className="muted">← SkySnR Vision</Link>
      <div className="card" style={{ marginTop: '1rem' }}>
        <h2>Sign in</h2>
        <ErrorMsg error={error} />
        <form onSubmit={submit} noValidate>
          <Field label="Email"><input type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username" /></Field>
          <Field label="Password">
            <input type={show ? 'text' : 'password'} value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
            <label style={{ fontWeight: 500, marginTop: '.4rem' }}><input type="checkbox" checked={show} onChange={(e) => setShow(e.target.checked)} /> Show password</label>
          </Field>
          <button className="btn" disabled={busy} style={{ width: '100%' }}>{busy ? 'Signing in…' : 'Sign in'}</button>
        </form>
        <p className="muted" style={{ marginTop: '1rem' }}>No account? <Link to="/register">Register</Link></p>
      </div>
    </div>
  );
}
