import type {Mission,Detection,Incident,Cls} from './types';
export const MISSIONS:Mission[]=[
{id:'M-FLOOD',name:'Flood Response',scenario:'flood',desc:'Flooded roads, waterlogged areas and affected settlements.',dataset:'Simulated dataset A',source:'Built-in demo scene',route:[[19.0720,72.8700],[19.0745,72.8760],[19.0780,72.8800],[19.0810,72.8870]]},
{id:'M-URBAN',name:'Urban Emergency',scenario:'urban',desc:'Dense settlement: people, vehicles, road access and obstructions.',dataset:'Simulated dataset B',source:'Built-in demo scene',route:[[19.0400,72.8400],[19.0440,72.8450],[19.0470,72.8520],[19.0500,72.8580]]},
{id:'M-SLIDE',name:'Landslide and Debris',scenario:'landslide',desc:'Hilly terrain, damaged roads and visible debris.',dataset:'Simulated dataset C',source:'Built-in demo scene',route:[[19.1100,72.9000],[19.1140,72.9050],[19.1170,72.9120],[19.1210,72.9170]]}];
const d=(m:string,n:number,cls:Cls,conf:number,box:[number,number,number,number],ts:string,lat:number,lng:number):Detection=>({id:`${m.slice(2,5)}-D${n}`,missionId:m,cls,conf,box,frame:parseInt(ts.slice(3))*24,ts,lat,lng,source:'demonstration',order:n,tracking:cls==='person'?`T${n}`:undefined});
export const DETECTIONS:Detection[]=[
d('M-FLOOD',1,'person',.92,[.12,.55,.05,.12],'00:04',19.0722,72.8712),d('M-FLOOD',2,'person',.81,[.40,.62,.05,.11],'00:09',19.0748,72.8765),d('M-FLOOD',3,'vehicle',.89,[.62,.50,.12,.08],'00:13',19.0782,72.8805),d('M-FLOOD',4,'obstacle',.77,[.30,.35,.14,.09],'00:17',19.0801,72.8850),d('M-FLOOD',5,'person',.58,[.78,.68,.05,.11],'00:21',19.0812,72.8868),
d('M-URBAN',1,'person',.88,[.20,.60,.05,.12],'00:03',19.0402,72.8410),d('M-URBAN',2,'vehicle',.94,[.50,.55,.13,.08],'00:08',19.0442,72.8455),d('M-URBAN',3,'vehicle',.72,[.70,.40,.12,.08],'00:12',19.0468,72.8515),d('M-URBAN',4,'obstacle',.85,[.35,.30,.15,.10],'00:16',19.0498,72.8575),
d('M-SLIDE',1,'obstacle',.91,[.25,.45,.20,.14],'00:05',19.1102,72.9004),d('M-SLIDE',2,'person',.66,[.55,.65,.05,.12],'00:10',19.1142,72.9052),d('M-SLIDE',3,'vehicle',.79,[.68,.58,.12,.08],'00:15',19.1168,72.9118),d('M-SLIDE',4,'obstacle',.47,[.10,.30,.12,.09],'00:19',19.1205,72.9165)];
const now=new Date().toISOString();
const inc=(n:number,det:Detection,status:any):Incident=>({id:`INC-00${n}`,detectionId:det.id,missionId:det.missionId,cls:det.cls,conf:det.conf,ts:det.ts,lat:det.lat,lng:det.lng,status,notes:[],created:now,updated:now,simulated:true,history:[{at:now,text:'Seeded simulated demonstration incident'}]});
export const INCIDENTS:Incident[]=[inc(1,DETECTIONS[0],'New'),inc(2,DETECTIONS[6],'Under Review'),inc(3,DETECTIONS[9],'Verified'),inc(4,DETECTIONS[10],'Dismissed')];
export const COLORS:Record<Cls,string>={person:'#FF7A1A',vehicle:'#39A4FF',obstacle:'#FF574F'};
export const LABEL:Record<Cls,string>={person:'Person',vehicle:'Vehicle',obstacle:'Obstacle'};
export const PLURAL:Record<Cls,string>={person:'People',vehicle:'Vehicles',obstacle:'Obstacles'};
// Generated aerial-style demo scenes (inline SVG, always loads)
export function scene(k:string){const c:any={flood:['#0c3a52','#1b6a8a','#7a6a4a'],urban:['#26323d','#3a4652','#6b5a48'],landslide:['#2f3a2a','#5a4a34','#7a6a52']}[k]||['#222','#333','#444'];
 let s=`<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 800 450'><defs><linearGradient id='g' x1='0' y1='0' x2='1' y2='1'><stop offset='0' stop-color='${c[0]}'/><stop offset='1' stop-color='${c[1]}'/></linearGradient></defs><rect width='800' height='450' fill='url(#g)'/>`;
 for(let i=0;i<26;i++){const x=(i*97)%780,y=(i*61)%420;s+=`<rect x='${x}' y='${y}' width='${30+(i*13)%50}' height='${20+(i*7)%36}' fill='${c[2]}' opacity='.${3+i%4}' rx='3'/>`}
 s+=`<path d='M0 300 Q300 250 520 320 T800 280' stroke='#0b0f12' stroke-width='26' fill='none' opacity='.55'/></svg>`;return 'data:image/svg+xml;utf8,'+encodeURIComponent(s)}
