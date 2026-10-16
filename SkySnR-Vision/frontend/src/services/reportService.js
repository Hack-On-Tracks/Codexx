import { request } from './api';
export const listReports = () => request('/reports');
export const generate = (mission_id, incident_id) => request('/reports/generate', { method: 'POST', body: { mission_id, incident_id: incident_id || null } });
