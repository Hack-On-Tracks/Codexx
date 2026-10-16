import { request } from './api';
export const listIncidents = (params = {}) => {
  const q = new URLSearchParams(Object.entries(params).filter(([, v]) => v)).toString();
  return request(`/incidents${q ? `?${q}` : ''}`);
};
export const getIncident = (id) => request(`/incidents/${id}`);
export const createIncident = (body) => request('/incidents', { method: 'POST', body });
export const team = () => request('/team');
export const assign = (id, member_id, notes = '') => request(`/incidents/${id}/assign`, { method: 'POST', body: { member_id, notes } });
export const updateNotes = (id, manager_notes) => request(`/incidents/${id}`, { method: 'PATCH', body: { manager_notes } });
export const acknowledge = (id) => request(`/incidents/${id}/acknowledge`, { method: 'POST' });
export const start = (id) => request(`/incidents/${id}/start`, { method: 'POST' });
export const resolve = (id, { outcome, field_observations, file }) => {
  const f = new FormData();
  f.append('outcome', outcome); f.append('field_observations', field_observations || '');
  if (file) f.append('file', file);
  return request(`/incidents/${id}/resolve`, { method: 'POST', form: f });
};
export const addNote = (id, notes) => request(`/incidents/${id}/events`, { method: 'POST', body: { notes } });
export const events = (id) => request(`/incidents/${id}/events`);
