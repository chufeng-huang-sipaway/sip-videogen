//useActiveJob - tracks active job state for todo/approval integration
import{useState,useEffect,useCallback}from'react'
import{bridge,isPyWebView,type SessionState,type ActiveJobState}from'@/lib/bridge'
import{eventBus,EVENT_NAMES}from'@/lib/eventBus'
interface UseActiveJobResult{
activeJob:ActiveJobState|null
isPaused:boolean
isGenerating:boolean
pause:()=>Promise<void>
resume:()=>Promise<void>
stop:()=>Promise<void>
stopWithNewDirection:(message:string)=>Promise<void>}
export function useActiveJob():UseActiveJobResult{
const[activeJob,setActiveJob]=useState<ActiveJobState|null>(null)
//Hydrate on mount
useEffect(()=>{
if(!isPyWebView())return
bridge.getSessionState().then((state:SessionState)=>{
setActiveJob(state.activeJob)}).catch(()=>{})
},[])
//Subscribe to job lifecycle events
useEffect(()=>{
const unsubs:Array<()=>void>=[]
//Job paused
unsubs.push(eventBus.subscribe(EVENT_NAMES.onJobPaused,(data:{runId:string})=>{
setActiveJob(prev=>prev&&prev.runId===data.runId?{...prev,isPaused:true}:prev)}))
//Job resumed
unsubs.push(eventBus.subscribe(EVENT_NAMES.onJobResumed,(data:{runId:string})=>{
setActiveJob(prev=>prev&&prev.runId===data.runId?{...prev,isPaused:false}:prev)}))
//Job interrupted (stopped/cancelled)
unsubs.push(eventBus.subscribe(EVENT_NAMES.onJobInterrupted,(_data:{runId:string})=>{
setActiveJob(null)}))
return()=>unsubs.forEach(u=>u())
},[])
const pause=useCallback(async()=>{
if(!isPyWebView()||!activeJob)return
await bridge.interruptTask('pause')
setActiveJob(prev=>prev?{...prev,isPaused:true}:prev)
},[activeJob])
const resume=useCallback(async()=>{
if(!isPyWebView()||!activeJob)return
const result=await bridge.resumeTask()
if(result.started){setActiveJob(prev=>prev?{...prev,isPaused:false,runId:result.runId}:prev)}
},[activeJob])
const stop=useCallback(async()=>{
if(!isPyWebView()||!activeJob)return
await bridge.interruptTask('stop')
setActiveJob(null)
},[activeJob])
const stopWithNewDirection=useCallback(async(message:string)=>{
if(!isPyWebView()||!activeJob)return
await bridge.interruptTask('new_direction',message)
setActiveJob(null)
},[activeJob])
return{
activeJob,
isPaused:activeJob?.isPaused??false,
isGenerating:!!activeJob&&!activeJob.isPaused,
pause,resume,stop,stopWithNewDirection}
}
