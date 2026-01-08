//AutonomyToggle - toggle for autonomous mode (auto-approve all operations)
import{useState,useEffect,useCallback}from'react'
import{Zap,ZapOff}from'lucide-react'
import{bridge,isPyWebView,type SessionState}from'@/lib/bridge'
import{eventBus,EVENT_NAMES}from'@/lib/eventBus'
import{cn}from'@/lib/utils'
import type{AutonomyChangedEvent}from'@/types/approval'
interface AutonomyToggleProps{
disabled?:boolean
className?:string}
export function AutonomyToggle({disabled,className}:AutonomyToggleProps){
const[autonomyMode,setAutonomyMode]=useState(false)
const[isLoading,setIsLoading]=useState(false)
//Hydrate on mount
useEffect(()=>{
if(!isPyWebView())return
bridge.getSessionState().then((state:SessionState)=>{
setAutonomyMode(state.autonomyMode)}).catch(()=>{})},[])
//Subscribe to autonomy changed events
useEffect(()=>{
const unsub=eventBus.subscribe<AutonomyChangedEvent>(EVENT_NAMES.onAutonomyChanged,(data)=>{
setAutonomyMode(data.enabled)})
return unsub},[])
const handleToggle=useCallback(async()=>{
if(!isPyWebView()||isLoading||disabled)return
setIsLoading(true)
try{
const newValue=!autonomyMode
await bridge.setAutonomyMode(newValue)
setAutonomyMode(newValue)}catch{}finally{setIsLoading(false)}},[autonomyMode,isLoading,disabled])
return(<button type="button" onClick={handleToggle} disabled={disabled||isLoading}
className={cn('inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-all',
autonomyMode?'bg-amber-500/20 text-amber-600 dark:text-amber-400 hover:bg-amber-500/30':'bg-muted text-muted-foreground hover:bg-muted/80',
(disabled||isLoading)&&'opacity-50 pointer-events-none',className)}
title={autonomyMode?'Autonomous mode ON - all operations auto-approved':'Autonomous mode OFF - approval required for sensitive operations'}>
{autonomyMode?<Zap className="h-3 w-3"/>:<ZapOff className="h-3 w-3"/>}
<span>{autonomyMode?'Auto':'Manual'}</span>
</button>)}
