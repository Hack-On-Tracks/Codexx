import {COLORS} from './data';import type {Cls} from './types';
const P={fill:'none',stroke:'currentColor',strokeWidth:1.9,strokeLinecap:'round' as const,strokeLinejoin:'round' as const};
export const Logo=({size=30}:{size?:number})=><svg width={size} height={size} viewBox="0 0 32 32" aria-hidden><g {...P} stroke="#FF7A1A"><circle cx="7" cy="7" r="3.2"/><circle cx="25" cy="7" r="3.2"/><circle cx="7" cy="25" r="3.2"/><circle cx="25" cy="25" r="3.2"/><path d="M9.5 9.5l4 4M22.5 9.5l-4 4M9.5 22.5l4-4M22.5 22.5l-4-4"/><circle cx="16" cy="16" r="4" stroke="#FF922E"/><circle cx="16" cy="16" r="1.4" fill="#FF922E"/></g></svg>;
export const ClsIcon=({c,size=20}:{c:Cls;size?:number})=>{const col={color:COLORS[c]};
 return <svg width={size} height={size} viewBox="0 0 24 24" style={col} aria-hidden><g {...P}>{c==='person'&&<><path d="M4 8V4h4M16 4h4v4M20 16v4h-4M8 20H4v-4"/><circle cx="12" cy="9" r="1.8"/><path d="M12 11.5v4M9.5 13h5M10.5 18l1.5-2.5 1.5 2.5"/></>}
 {c==='vehicle'&&<><rect x="8" y="3" width="8" height="18" rx="3"/><path d="M8.5 8h7M8.5 16h7M5 7v2M19 7v2M5 15v2M19 15v2"/></>}
 {c==='obstacle'&&<><path d="M3 20h18M5 20V9M19 20V9M3 9h18v4H3zM3 13l4 -4M9 13l4-4M15 13l4-4"/></>}</g></svg>};
export const markerSvg=(c:Cls|'drone',sel=false)=>{const col=c==='drone'?'#FF7A1A':COLORS[c];
 const inner={person:'<circle cx="12" cy="8.5" r="2"/><path d="M8 18c0-3 1.8-5 4-5s4 2 4 5"/>',vehicle:'<rect x="9" y="5" width="6" height="14" rx="2.5"/><path d="M9.5 9h5M9.5 15h5"/>',obstacle:'<path d="M12 5l7 13H5z"/><path d="M12 10v3.5M12 16h.01"/>',drone:'<circle cx="7" cy="7" r="2"/><circle cx="17" cy="7" r="2"/><circle cx="7" cy="17" r="2"/><circle cx="17" cy="17" r="2"/><path d="M9 9l6 6M15 9l-6 6"/>'}[c];
 return `<svg xmlns="http://www.w3.org/2000/svg" width="${sel?42:34}" height="${sel?42:34}" viewBox="0 0 24 24"><circle cx="12" cy="12" r="11" fill="#06131C" stroke="${col}" stroke-width="${sel?2.2:1.2}"/>${sel?`<circle cx="12" cy="12" r="11.6" fill="none" stroke="#fff" stroke-width=".6"/>`:''}<g fill="none" stroke="${col}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">${inner}</g></svg>`};
const S=(c:any)=>({width:18,height:18,viewBox:'0 0 24 24','aria-hidden':true,style:{flex:'none'},children:<g {...P}>{c}</g>});
export const LogoMono=({size=30}:{size?:number})=><svg width={size} height={size} viewBox="0 0 32 32" aria-hidden><g {...P} stroke="currentColor"><circle cx="7" cy="7" r="3.2"/><circle cx="25" cy="7" r="3.2"/><circle cx="7" cy="25" r="3.2"/><circle cx="25" cy="25" r="3.2"/><path d="M9.5 9.5l4 4M22.5 9.5l-4 4M9.5 22.5l4-4M22.5 22.5l-4-4"/><circle cx="16" cy="16" r="4"/></g></svg>;
export function ModIcon({k}:{k:string}){const m:any={
 Home:<><rect x="3" y="4" width="18" height="13" rx="2"/><path d="M7 13l3-3 3 2 4-5M8 21h8M12 17v4"/></>,
 Simulation:<><circle cx="6" cy="6" r="2"/><circle cx="18" cy="6" r="2"/><path d="M8 7l3 3M16 7l-3 3"/><rect x="9.5" y="10" width="5" height="4" rx="1"/><path d="M11 18l4 2-4 2z"/></>,
 'Rescue Map':<><path d="M12 21s-6-5.2-6-10a6 6 0 0112 0c0 4.8-6 10-6 10z"/><circle cx="12" cy="11" r="2"/><path d="M2 11h2M20 11h2"/></>,
 Incidents:<><path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4M12 11v4M12 18h.01"/></>,
 Upload:<><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M12 16v-6M9 12l3-3 3 3"/></>,
 Confidence:<><circle cx="12" cy="12" r="8"/><path d="M12 4a8 8 0 018 8"/><circle cx="12" cy="12" r="1.5"/></>,
 DronePath:<><circle cx="18" cy="6" r="2"/><path d="M16 8l-2 2M3 20c3 0 3-6 6-6s3 4 5 0" strokeDasharray="3 3"/></>,
 Mission:<><circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3"/><path d="M12 12l5-5"/></>};
 return <svg {...S(m[k]||m.Home)}/>}
