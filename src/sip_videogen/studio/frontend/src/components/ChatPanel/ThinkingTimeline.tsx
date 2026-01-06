//ThinkingTimeline - Timeline UI for agent reasoning steps
import { useState, type ReactNode } from 'react'
import { ChevronDown, Loader2 } from 'lucide-react'
import type { ThinkingStep, ImageGenerationMetadata } from '@/lib/bridge'
import { GenerationSummary } from './GenerationSummary'
import { cn } from '@/lib/utils'
//Expertise -> emoji mapping (UI adds emoji to plain labels from backend)
const EXPERTISE_EMOJI: Record<string,string>={
'Visual Design':'🎨','Brand Strategy':'📊','Strategy':'📊','Copywriting':'✍️',
'Image Generation':'🖼️','Video Generation':'🎬','Research':'🔍','Validation':'✅',
'Product Setup':'📦','Targeting':'🎯','Brainstorming':'💡',
}
function formatExpertise(exp:string|undefined):string{if(!exp)return '';const em=EXPERTISE_EMOJI[exp]||'';return em?`${em} ${exp}`:exp}
//Step status markers
function StepMarker({status,isActive}:{status:string;isActive:boolean}){
const base='w-3 h-3 rounded-full flex-shrink-0 transition-all duration-300'
if(status==='failed')return<span className={cn(base,'text-destructive')} aria-label="Failed">✗</span>
if(isActive)return<span className={cn(base,'bg-primary animate-pulse')} aria-label="In progress"/>
if(status==='pending')return<span className={cn(base,'border-2 border-muted-foreground/50')} aria-label="Pending"/>
return<span className={cn(base,'bg-success/80')} aria-label="Complete"/>
}
interface TimelineItemProps{step:ThinkingStep;isActive:boolean;isLast:boolean;expandedContent?:ReactNode}
function TimelineItem({step,isActive,isLast,expandedContent}:TimelineItemProps){
const [exp,setExp]=useState(false)
const hasCont=Boolean(step.detail||expandedContent)
const isFailed=step.status==='failed'
return(<div className="relative flex gap-2" role="listitem" aria-label={`${step.step}${step.expertise?` - ${step.expertise}`:''}`}>
{/* Vertical connector line */}
{!isLast&&<div className="absolute left-[5px] top-4 w-0.5 h-[calc(100%-8px)] bg-border/60"/>}
{/* Marker */}
<div className="relative z-10 mt-0.5"><StepMarker status={step.status||'complete'} isActive={isActive}/></div>
{/* Content */}
<div className={cn('flex-1 min-w-0 pb-3 transition-opacity duration-200',isActive?'opacity-100':isFailed?'opacity-50':'opacity-60')}>
<button type="button" onClick={()=>hasCont&&setExp(p=>!p)} className={cn('flex items-start gap-2 w-full text-left rounded px-1 py-0.5 transition-colors',hasCont?'hover:bg-muted/50 cursor-pointer':'')} aria-expanded={hasCont?exp:undefined}>
<div className="flex-1 min-w-0">
{step.expertise&&<span className="text-[10px] font-medium text-muted-foreground mr-2">{formatExpertise(step.expertise)}</span>}
<span className={cn('text-sm',isFailed?'line-through text-muted-foreground':'text-foreground')}>{step.step}</span>
</div>
{hasCont&&<ChevronDown className={cn('h-3 w-3 text-muted-foreground mt-1 transition-transform',exp?'rotate-0':'rotate-[-90deg]')}/>}
</button>
{exp&&<div className="pl-1 pr-2 pt-1">{expandedContent||(step.detail&&<div className="text-muted-foreground text-xs">{step.detail}</div>)}</div>}
</div>
</div>)}
interface Props{steps:ThinkingStep[];isGenerating:boolean;skills?:string[];imageMetadata?:ImageGenerationMetadata|null;onViewFullDetails?:()=>void}
export function ThinkingTimeline({steps,isGenerating,skills,imageMetadata,onViewFullDetails}:Props){
const [collapsed,setCollapsed]=useState(false)
//Only show spinner if generating with no steps AND no metadata
if(steps.length===0&&!imageMetadata){if(!isGenerating)return null
return(<div className="flex items-center gap-2 text-sm text-muted-foreground py-2 px-1"><Loader2 className="h-4 w-4 animate-spin"/><span>Processing...</span></div>)}
//Sort by seq (stable order)
const sorted=[...steps].sort((a,b)=>(a.seq??0)-(b.seq??0))
//Determine active step: last pending, or if generating + all complete, highlight last
const activeIdx=isGenerating?sorted.findIndex(s=>s.status==='pending'):-1
const effectiveActive=activeIdx>=0?activeIdx:(isGenerating&&sorted.length>0?sorted.length-1:-1)
//Calculate total including synthetic metadata step
const totalSteps=sorted.length+(imageMetadata?1:0)
//Collapsed view
if(collapsed&&!isGenerating&&totalSteps>0){return(<button type="button" onClick={()=>setCollapsed(false)} className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors py-1 px-1" aria-expanded={false}>
<ChevronDown className="h-3 w-3 rotate-[-90deg]"/><span>View {totalSteps} thinking step{totalSteps>1?'s':''}</span>
</button>)}
return(<div className="py-2" role="list" aria-label="Agent thinking steps">
{/* Skills badges */}
{skills&&skills.length>0&&(<div className="flex flex-wrap gap-1.5 mb-2 overflow-x-auto">{skills.slice(0,5).map((sk)=>(<span key={sk} className="text-[9px] uppercase tracking-wider text-muted-foreground border border-border/40 px-1.5 py-0.5 rounded-sm whitespace-nowrap">{sk.length>25?sk.slice(0,22)+'...':sk}</span>))}{skills.length>5&&(<span className="text-[9px] text-muted-foreground">+{skills.length-5} more</span>)}</div>)}
{/* Timeline items */}
{sorted.map((s,i)=>(<TimelineItem key={s.id} step={s} isActive={i===effectiveActive} isLast={i===sorted.length-1&&!imageMetadata}/>))}
{/* Generating indicator */}
{isGenerating&&activeIdx<0&&sorted.length>0&&(<div className="flex items-center gap-2 text-sm text-muted-foreground px-1 pl-5"><Loader2 className="h-3 w-3 animate-spin"/><span>Working...</span></div>)}
{/* Metadata-based result step */}
{!isGenerating&&imageMetadata&&(<TimelineItem key="synthetic-gen-details" step={{id:'synthetic-gen-details',step:'Generation complete',detail:'',status:'complete',seq:999,runId:'',source:'auto'}} isActive={false} isLast={true} expandedContent={<GenerationSummary metadata={imageMetadata} onViewFullDetails={onViewFullDetails}/>}/>)}
{/* Collapse button */}
{!isGenerating&&totalSteps>1&&(<button type="button" onClick={()=>setCollapsed(true)} className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors mt-1 px-1" aria-expanded={true}>
<ChevronDown className="h-3 w-3"/><span>Collapse</span>
</button>)}
</div>)}
//Re-export as ThinkingSteps for backward compatibility
export { ThinkingTimeline as ThinkingSteps }
