const BASE = import.meta.env.VITE_API_BASE || '/api';

export class ApiError extends Error {
  constructor(message, status) { super(message); this.status = status; }
}

function messageFrom(data, status) {
  const d = data && data.detail;
  if (typeof d === 'string') return d;
  if (Array.isArray(d)) return d.map((e) => (e.msg || '').replace(/^Value error, /, '')).join('. ');
  if (status === 503) return 'The service is unavailable. Please try again.';
  return 'Something went wrong. Please try again.';
}

export async function request(path, { method = 'GET', body, form } = {}) {
  const opts = { method, credentials: 'include', headers: {} };
  if (form) opts.body = form;
  else if (body !== undefined) { opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(body); }
  let res;
  try { res = await fetch(BASE + path, opts); }
  catch { throw new ApiError('Cannot reach the server. Check that the backend is running.', 0); }
  let data = null;
  try { data = await res.json(); } catch { /* empty body */ }
  if (!res.ok) {
    if (res.status === 401 && !path.startsWith('/auth/login')) window.dispatchEvent(new Event('auth:expired'));
    throw new ApiError(messageFrom(data, res.status), res.status);
  }
  return data;
}

export const mediaUrl = (ref) => (ref ? `${BASE}/media/${ref}` : null);
export const downloadUrl = (reportId) => `${BASE}/reports/${reportId}/download`;
