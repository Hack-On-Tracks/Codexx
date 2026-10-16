import { request } from './api';
export const listMissions = () => request('/missions');
export const getMission = (id) => request(`/missions/${id}`);
export const createMission = (body) => request('/missions', { method: 'POST', body });
export const analyze = (id, file) => { const f = new FormData(); f.append('file', file); return request(`/missions/${id}/analyze`, { method: 'POST', form: f }); };
export const missionDetections = (id) => request(`/missions/${id}/detections`);
export const setPriority = (id, body) => request(`/detections/${id}/priority`, { method: 'POST', body });
export const reviewDetection = (id, body) => request(`/detections/${id}/review`, { method: 'POST', body });
export const appConfig = () => request('/health');
