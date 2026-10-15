import type {Detection,Cls} from './types';
// Service layer: connect a real model by setting VITE_DETECT_URL (POST multipart "file" -> {detections:[{id,cls,conf,box:[x,y,w,h] normalized,frame?,ts?,lat?,lng?,tracking?}]}).
const URL_=(import.meta as any).env?.VITE_DETECT_URL as string|undefined;
export const isConfigured=()=>!!URL_;
export const MAX_MB=50;
export const IMG=['image/jpeg','image/png','image/webp'];export const VID=['video/mp4','video/webm'];
export function validateFile(f:File):string|null{
 if(![...IMG,...VID].includes(f.type))return `Unsupported format "${f.type||f.name.split('.').pop()}". Use JPG, PNG, WebP, MP4 or WebM.`;
 if(f.size>MAX_MB*1024*1024)return `File is ${(f.size/1048576).toFixed(1)} MB. The limit is ${MAX_MB} MB.`;return null}
const okBox=(b:any)=>Array.isArray(b)&&b.length===4&&b.every(n=>typeof n==='number'&&n>=0&&n<=1);
export async function analyze(file:File,missionId:string):Promise<Detection[]>{
 if(!URL_)throw new Error('No computer-vision model is connected. Set VITE_DETECT_URL to an inference endpoint. Demo scenarios use labelled sample detections instead.');
 const ctl=new AbortController();const t=setTimeout(()=>ctl.abort(),60000);
 try{const fd=new FormData();fd.append('file',file);const r=await fetch(URL_,{method:'POST',body:fd,signal:ctl.signal});
  if(!r.ok)throw new Error(`Analysis service returned ${r.status}.`);const j=await r.json();
  if(!j||!Array.isArray(j.detections))throw new Error('Invalid response from analysis service.');
  return j.detections.filter((d:any)=>['person','vehicle','obstacle'].includes(d.cls)&&d.conf>=0&&d.conf<=1&&okBox(d.box)).map((d:any,i:number)=>({id:d.id||`${missionId}-D${i+1}`,missionId,cls:d.cls as Cls,conf:d.conf,box:d.box,frame:d.frame,ts:d.ts||'00:00',lat:d.lat,lng:d.lng,tracking:d.tracking,source:'model' as const,order:i}))}
 catch(e:any){throw new Error(e.name==='AbortError'?'Analysis timed out after 60 seconds.':e.message||'Network error.')}finally{clearTimeout(t)}}
