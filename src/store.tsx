import {createContext,useContext,useEffect,useState,ReactNode} from 'react';
import {DETECTIONS,INCIDENTS,MISSIONS} from './data';import type {Detection,Incident,Status,Mission} from './types';
interface Notif{id:string;text:string;read:boolean;at:string;demo?:boolean}
interface S{missions:Mission[];detections:Detection[];incidents:Incident[];notifs:Notif[];
 addMission:(m:Mission,d:Detection[])=>void;createIncident:(d:Detection)=>Incident|null;setStatus:(id:string,s:Status)=>void;addNote:(id:string,t:string)=>void;
 notify:(t:string)=>void;readAll:()=>void;reset:()=>void;toast:(t:string)=>void;toastMsg:string}
const Ctx=createContext<S>(null as any);export const useStore=()=>useContext(Ctx);
const KEY='skysnr-v1';
function load(){try{const j=localStorage.getItem(KEY);if(j)return JSON.parse(j)}catch{}return null}
const seed=()=>({missions:MISSIONS,detections:DETECTIONS,incidents:INCIDENTS,notifs:[{id:'n1',text:'Simulated: obstacle detected in Landslide and Debris',read:false,at:new Date().toISOString(),demo:true},{id:'n2',text:'Simulated: incident INC-002 under review',read:false,at:new Date().toISOString(),demo:true}]});
export function Provider({children}:{children:ReactNode}){
 const [st,setSt]=useState<any>(()=>load()||seed());const [toastMsg,setT]=useState('');
 useEffect(()=>{try{localStorage.setItem(KEY,JSON.stringify(st))}catch{setT('Browser storage is unavailable. Changes will not persist after refresh.')}},[st]);
 const toast=(t:string)=>{setT(t);setTimeout(()=>setT(''),3000)};
 const n=(t:string)=>({id:crypto.randomUUID(),text:t,read:false,at:new Date().toISOString()});
 const api:S={...st,toastMsg,toast,
  addMission:(m,d)=>setSt((s:any)=>({...s,missions:[...s.missions.filter((x:any)=>x.id!==m.id),m],detections:[...s.detections.filter((x:any)=>x.missionId!==m.id),...d],notifs:[n(`Analysis completed for ${m.name}`),...s.notifs]})),
  createIncident:(d)=>{if(d.incidentId)return null;const now=new Date().toISOString();const id=`INC-${String(st.incidents.length+1).padStart(3,'0')}`;
   const i:Incident={id,detectionId:d.id,missionId:d.missionId,cls:d.cls,conf:d.conf,ts:d.ts,lat:d.lat,lng:d.lng,status:'New',notes:[],created:now,updated:now,simulated:d.source==='demonstration',history:[{at:now,text:'Incident created'}]};
   setSt((s:any)=>({...s,incidents:[...s.incidents,i],detections:s.detections.map((x:any)=>x.id===d.id?{...x,incidentId:id}:x),notifs:[n(`Incident ${id} created`),...s.notifs]}));toast(`Incident ${id} created`);return i},
  setStatus:(id,status)=>setSt((s:any)=>({...s,incidents:s.incidents.map((i:any)=>i.id===id?{...i,status,updated:new Date().toISOString(),history:[...i.history,{at:new Date().toISOString(),text:i.status==='Dismissed'?`Reopened as ${status}`:`Status changed to ${status}`}]}:i),notifs:[n(`Incident ${id} status updated: ${status}`),...s.notifs]})),
  addNote:(id,t)=>setSt((s:any)=>({...s,incidents:s.incidents.map((i:any)=>i.id===id?{...i,notes:[...i.notes,t],updated:new Date().toISOString(),history:[...i.history,{at:new Date().toISOString(),text:'Note added'}]}:i)})),
  notify:t=>setSt((s:any)=>({...s,notifs:[n(t),...s.notifs]})),readAll:()=>setSt((s:any)=>({...s,notifs:s.notifs.map((x:any)=>({...x,read:true}))})),
  reset:()=>{setSt(seed());toast('Demonstration data reset')}};
 return <Ctx.Provider value={api}>{children}{toastMsg&&<div className="toast" role="status">{toastMsg}</div>}</Ctx.Provider>}
