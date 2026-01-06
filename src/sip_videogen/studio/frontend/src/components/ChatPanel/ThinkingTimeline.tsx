//ThinkingTimeline - Flat single-level timeline for agent reasoning steps
import { useState, useEffect } from 'react'
import { Loader2, CheckCircle2, ChevronRight } from 'lucide-react'
import type { ThinkingStep, ImageGenerationMetadata } from '@/lib/bridge'
import { cn } from '@/lib/utils'
//Expertise -> emoji mapping
const EXPERTISE_EMOJI: Record<string,string>={'Visual Design':'🎨','Brand Strategy':'📊','Strategy':'📊','Copywriting':'✍️','Image Generation':'🖼️','Video Generation':'🎬','Research':'🔍','Validation':'✅','Product Setup':'📦','Targeting':'🎯','Brainstorming':'💡'}
function getExpertiseEmoji(exp:string|undefined):string{return exp?EXPERTISE_EMOJI[exp]||'💭':'💭'}
//Simple flat step - emoji at start, single line
function TimelineStep({step,isActive,isFailed}:{step:ThinkingStep;isActive:boolean;isFailed:boolean}){
const emoji=getExpertiseEmoji(step.expertise)
return(<div className={cn('flex items-center gap-2 py-0.5 text-xs',isActive&&'animate-step-breathing text-foreground font-medium',!isActive&&!isFailed&&'text-muted-foreground opacity-70',isFailed&&'text-muted-foreground opacity-40 line-through')}>
<span className="flex-shrink-0">{emoji}</span>
<span className="flex-1">{step.step}</span>
</div>)}
interface Props{steps:ThinkingStep[];isGenerating:boolean;skills?:string[];imageMetadata?:ImageGenerationMetadata|null;onViewFullDetails?:()=>void}
export function ThinkingTimeline({steps,isGenerating,imageMetadata}:Props){
const [expanded,setExpanded]=useState(true)
useEffect(()=>{if(!isGenerating&&steps.length>0)setExpanded(false)},[isGenerating,steps.length])
useEffect(()=>{if(isGenerating)setExpanded(true)},[isGenerating])
if(steps.length===0&&!imageMetadata){
if(!isGenerating)return null
return<div className="flex items-center gap-2 text-xs text-muted-foreground py-1"><Loader2 className="h-3 w-3 animate-spin"/><span>Thinking...</span></div>
}
const sorted=[...steps].sort((a,b)=>(a.seq??0)-(b.seq??0))
const effectiveActive=isGenerating&&sorted.length>0?sorted.length-1:-1
const totalSteps=sorted.length
//Collapsed summary view
if(!expanded&&!isGenerating&&totalSteps>0){
return(<button type="button" onClick={()=>setExpanded(true)} className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground transition-colors py-1 group">
<CheckCircle2 className="h-3.5 w-3.5 text-success/70"/>
<span>{totalSteps} step{totalSteps>1?'s':''} completed</span>
<ChevronRight className="h-3 w-3 opacity-50 group-hover:opacity-100 transition-opacity"/>
</button>)}
//Expanded flat timeline
return(<div className={cn('py-1 pl-3',sorted.length>1&&'border-l-2 border-border/50')} role="list" aria-label="Agent thinking steps">
{sorted.map((s,i)=><TimelineStep key={s.id} step={s} isActive={i===effectiveActive} isFailed={s.status==='failed'}/>)}
{!isGenerating&&expanded&&sorted.length>1&&<button type="button" onClick={()=>setExpanded(false)} className="text-[11px] text-muted-foreground/40 hover:text-muted-foreground transition-colors mt-1">Hide</button>}
</div>)}
export { ThinkingTimeline as ThinkingSteps }
