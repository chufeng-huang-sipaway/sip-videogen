//useApproval hook - manages approval requests from backend push events
import{useState,useEffect,useCallback}from'react'
import{eventBus,EVENT_NAMES}from'@/lib/eventBus'
import{bridge,isPyWebView,type SessionState}from'@/lib/bridge'
import type{ApprovalRequest,ApprovalAction,ApprovalRequestEvent,ApprovalClearedEvent}from'@/types/approval'
interface UseApprovalResult{
pendingApproval:ApprovalRequest|null
isApprovalPending:boolean
//Actions
respondApprove:()=>Promise<void>
respondReject:()=>Promise<void>
respondEdit:(modifiedPrompt:string)=>Promise<void>
respondApproveAll:()=>Promise<void>}
export function useApproval():UseApprovalResult{
const[pendingApproval,setPendingApproval]=useState<ApprovalRequest|null>(null)
//Hydrate on mount
useEffect(()=>{
if(!isPyWebView())return
bridge.getSessionState().then((state:SessionState)=>{
setPendingApproval(state.pendingApproval)}).catch(()=>{})},[])
//Subscribe to approval events
useEffect(()=>{
const unsubs:Array<()=>void>=[]
//Approval request received
unsubs.push(eventBus.subscribe<ApprovalRequestEvent>(EVENT_NAMES.onApprovalRequest,(data)=>{
setPendingApproval(data)}))
//Approval cleared (resolved via any path: approve/reject/timeout/cancel)
unsubs.push(eventBus.subscribe<ApprovalClearedEvent>(EVENT_NAMES.onApprovalCleared,(data)=>{
setPendingApproval(prev=>{
if(prev&&prev.id===data.requestId)return null
return prev})}))
return()=>unsubs.forEach(u=>u())},[])
const respond=useCallback(async(action:ApprovalAction,modifiedPrompt?:string)=>{
if(!isPyWebView()||!pendingApproval)return
try{await bridge.respondToApproval(pendingApproval.id,action,modifiedPrompt)
setPendingApproval(null)}catch{}},[pendingApproval])
const respondApprove=useCallback(()=>respond('approve'),[respond])
const respondReject=useCallback(()=>respond('reject'),[respond])
const respondEdit=useCallback((modifiedPrompt:string)=>respond('edit',modifiedPrompt),[respond])
const respondApproveAll=useCallback(()=>respond('approve_all'),[respond])
return{
pendingApproval,
isApprovalPending:!!pendingApproval,
respondApprove,respondReject,respondEdit,respondApproveAll}}
