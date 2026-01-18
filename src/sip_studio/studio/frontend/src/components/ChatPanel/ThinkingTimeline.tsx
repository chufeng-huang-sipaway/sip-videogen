//ThinkingTimeline - Flat single-level timeline for agent reasoning steps
import { useState, useEffect } from 'react'
import { Loader2, CheckCircle2, ChevronRight, Globe, Sparkles, Package, Palette, Building2, ScanLine, Film, Wrench, FileText, FolderOpen, Brain } from 'lucide-react'
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
//Tool name -> icon and friendly label mapping
const TOOL_CONFIG:Record<string,{icon:typeof Sparkles;label:string}>={
  generate_image:{icon:Sparkles,label:'Creating image...'},
  generate_video_clip:{icon:Film,label:'Creating video...'},
  manage_product:{icon:Package,label:'Managing product...'},
  manage_style_reference:{icon:Palette,label:'Updating style...'},
  get_style_reference:{icon:Palette,label:'Loading style...'},
  analyze_packaging:{icon:ScanLine,label:'Analyzing packaging...'},
  update_packaging_text:{icon:FileText,label:'Updating text...'},
  load_brand:{icon:Building2,label:'Loading brand...'},
  list_products:{icon:Package,label:'Listing products...'},
  get_product_detail:{icon:Package,label:'Loading product...'},
  fetch_brand_detail:{icon:Building2,label:'Fetching details...'},
  browse_brand_assets:{icon:FolderOpen,label:'Browsing assets...'},
  read_file:{icon:FileText,label:'Reading file...'},
  write_file:{icon:FileText,label:'Writing file...'},
  list_files:{icon:FolderOpen,label:'Listing files...'},
  web_search:{icon:Globe,label:'Searching web...'},
  request_deep_research:{icon:Globe,label:'Starting research...'},
  activate_skill:{icon:Brain,label:'Activating skill...'},
  propose_choices:{icon:Brain,label:'Preparing options...'},
  propose_images:{icon:Sparkles,label:'Preparing images...'},
}
function getToolConfig(name:string):{icon:typeof Sparkles;label:string}{return TOOL_CONFIG[name]||{icon:Wrench,label:`Running ${name.replace(/_/g,' ')}...`}}
//Tool badge - breathing animation showing current tool being called
function ToolBadge({toolName}:{toolName:string}){
const{icon:Icon,label}=getToolConfig(toolName)
return(<div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-brand-500/10 backdrop-blur-sm border border-brand-500/20 text-brand-500 text-[11px] font-medium shadow-sm">
<div className="relative flex items-center justify-center">
<div className="absolute inset-0 bg-brand-500/30 blur-md rounded-full animate-pulse"/>
<Icon className="h-3.5 w-3.5 relative z-10 animate-pulse"/>
</div>
<span className="animate-pulse">{label}</span>
</div>)}
//Web search breathing badge - shows when web search mode is active during generation
function WebSearchBadge(){return(
<div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-brand-500/10 text-brand-500 text-[11px] font-medium animate-pulse">
<Globe className="h-3 w-3"/>
<span>Searching</span>
</div>)}
interface Props{steps:ThinkingStep[];isGenerating:boolean;skills?:string[];imageMetadata?:ImageGenerationMetadata|null;onViewFullDetails?:()=>void;webSearchActive?:boolean;currentTool?:{name:string;startedAt:number}|null}
export function ThinkingTimeline({steps,isGenerating,imageMetadata,webSearchActive,currentTool}:Props){
const [expanded,setExpanded]=useState(true)
useEffect(()=>{if(!isGenerating&&steps.length>0)setExpanded(false)},[isGenerating,steps.length])
useEffect(()=>{if(isGenerating)setExpanded(true)},[isGenerating])
if(steps.length===0&&!imageMetadata){
if(!isGenerating)return null
return(<div className="flex items-center gap-2 text-xs text-muted-foreground py-1">
{currentTool?<ToolBadge toolName={currentTool.name}/>:webSearchActive?<WebSearchBadge/>:<><Loader2 className="h-3 w-3 animate-spin"/><span>Thinking...</span></>}
</div>)
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
{isGenerating&&<div className="mb-1">{currentTool?<ToolBadge toolName={currentTool.name}/>:webSearchActive?<WebSearchBadge/>:null}</div>}
{sorted.map((s,i)=><TimelineStep key={s.id} step={s} isActive={i===effectiveActive} isFailed={s.status==='failed'}/>)}
{!isGenerating&&expanded&&sorted.length>1&&<button type="button" onClick={()=>setExpanded(false)} className="text-[11px] text-muted-foreground/40 hover:text-muted-foreground transition-colors mt-1">Hide</button>}
</div>)}
export { ThinkingTimeline as ThinkingSteps }
