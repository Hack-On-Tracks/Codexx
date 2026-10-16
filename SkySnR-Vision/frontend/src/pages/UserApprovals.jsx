import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import * as auth from '../services/authService';
import { Badge, Empty, ErrorMsg, Loading, Modal, Notice, ROLE_SHORT, Tabs, fmt } from '../components/ui';

export default function UserApprovals() {
  const [params, setParams] = useSearchParams();
  const status = params.get('status') || '';
  const roleFilter = params.get('role') || '';
  const [users, setUsers] = useState(null);
  const [error, setError] = useState('');
  const [ok, setOk] = useState('');
  const [busy, setBusy] = useState('');
  const [detail, setDetail] = useState(null);

  const load = useCallback(() => auth.listUsers(status).then((u) => setUsers(roleFilter ? u.filter((x) => x.role === roleFilter) : u)).catch((e) => setError(e.message)), [status, roleFilter]);
  useEffect(() => { setUsers(null); load(); }, [load]);

  async function act(fn, u, msg) {
    setBusy(u.id); setError(''); setOk('');
    try { await fn(u.id); setOk(msg); await load(); } catch (e) { setError(e.message); await load(); } finally { setBusy(''); }
  }

  return (
    <div className="stack">
      <h1>User approvals</h1>
      <Tabs value={status} onChange={(v) => setParams(v ? { status: v } : {})} options={[['', 'All'], ['pending', 'Pending'], ['approved', 'Approved'], ['rejected', 'Rejected']]} />
      <ErrorMsg error={error} /><Notice>{ok}</Notice>
      {!users ? <Loading /> : users.length === 0 ? <Empty>No users match this filter.</Empty> : (
        <div className="card table-wrap"><table>
          <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Registered</th><th>Status</th><th>Actions</th></tr></thead>
          <tbody>{users.map((u) => (
            <tr key={u.id}>
              <td>{u.full_name}</td><td>{u.email}</td><td>{ROLE_SHORT[u.role]}</td><td>{fmt(u.created_at)}</td>
              <td><Badge value={u.approval_status} />{u.approval_status === 'approved' && !u.is_active && <> <Badge value="rejected" label="Inactive" /></>}</td>
              <td><div className="row">
                <button className="btn sm quiet" onClick={() => setDetail(u)}>Details</button>
                {u.approval_status === 'pending' && <>
                  <button className="btn sm" disabled={busy === u.id} onClick={() => act(auth.approveUser, u, `${u.full_name} approved.`)}>Approve</button>
                  <button className="btn sm secondary" disabled={busy === u.id} onClick={() => act(auth.rejectUser, u, `${u.full_name} rejected.`)}>Reject</button></>}
                {u.approval_status === 'approved' && u.role !== 'admin' &&
                  <button className="btn sm secondary" disabled={busy === u.id} onClick={() => act((id) => auth.setUserActive(id, !u.is_active), u, u.is_active ? 'Account deactivated.' : 'Account activated.')}>{u.is_active ? 'Deactivate' : 'Activate'}</button>}
              </div></td>
            </tr>))}</tbody></table></div>)}
      {detail && <Modal title={detail.full_name} onClose={() => setDetail(null)}>
        <p><strong>Email:</strong> {detail.email}</p><p><strong>Role:</strong> {ROLE_SHORT[detail.role]}</p>
        <p><strong>Registered:</strong> {fmt(detail.created_at)}</p><p><strong>Approval:</strong> <Badge value={detail.approval_status} /></p>
        <p><strong>Active:</strong> {detail.is_active ? 'Yes' : 'No'}</p></Modal>}
    </div>
  );
}
