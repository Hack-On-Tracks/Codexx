export type Cls='person'|'vehicle'|'obstacle';
export type Status='New'|'Under Review'|'Verified'|'Dismissed';
export interface Detection{id:string;missionId:string;cls:Cls;conf:number;box:[number,number,number,number];frame?:number;ts:string;lat?:number;lng?:number;tracking?:string;incidentId?:string;source:'demonstration'|'model';order:number}
export interface Mission{id:string;name:string;scenario:string;desc:string;dataset:string;source:string;route:[number,number][]}
export interface Incident{id:string;detectionId:string;missionId:string;cls:Cls;conf:number;ts:string;lat?:number;lng?:number;status:Status;notes:string[];created:string;updated:string;history:{at:string;text:string}[];simulated:boolean}
