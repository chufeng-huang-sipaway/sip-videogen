//ThinkingSteps component - displays agent reasoning steps
import { useState, type ReactNode } from 'react'
import { ChevronRight, ChevronDown, CheckCircle2, Loader2 } from 'lucide-react'
import type { ThinkingStep, ImageGenerationMetadata } from '@/lib/bridge'
import { PromptDiff } from './PromptDiff'
import { GenerationSummary } from './GenerationSummary'
interface Props {steps:ThinkingStep[];isGenerating:boolean;skills?:string[];imageMetadata?:ImageGenerationMetadata|null;onViewFullDetails?:()=>void}
export function ThinkingSteps({steps,isGenerating,skills,imageMetadata,onViewFullDetails}:Props){
//Only show spinner if generating with no steps AND no metadata
if(steps.length===0&&!imageMetadata){if(!isGenerating)return null
return(<div className="flex items-center gap-2 text-sm text-muted-foreground py-2 px-1"><Loader2 className="h-4 w-4 animate-spin"/><span>Processing...</span></div>)}
return(<div className="space-y-1 py-2">
{skills&&skills.length>0&&(<div className="flex flex-wrap gap-1.5 mb-2 overflow-x-auto">{skills.slice(0,5).map((sk)=>(<span key={sk} className="text-[9px] uppercase tracking-wider text-muted-foreground border border-border/40 px-1.5 py-0.5 rounded-sm whitespace-nowrap">{sk.length>25?sk.slice(0,22)+'...':sk}</span>))}{skills.length>5&&(<span className="text-[9px] text-muted-foreground">+{skills.length-5} more</span>)}</div>)}
{steps.map((s)=>(<StepItem key={s.id} step={s}/>))}
{isGenerating&&(<div className="flex items-center gap-2 text-sm text-muted-foreground px-1"><Loader2 className="h-3 w-3 animate-spin"/><span>Working...</span></div>)}
{/* Metadata-based steps - only show when NOT generating and metadata exists */}
{!isGenerating&&imageMetadata&&(<>
<StepItem key="synthetic-prompt-diff" step={{id:'synthetic-prompt-diff',step:'Prompt enhancement',detail:'',timestamp:0}} expandedContent={<PromptDiff originalPrompt={imageMetadata.original_prompt||''} finalPrompt={imageMetadata.prompt||''}/>}/>
<StepItem key="synthetic-gen-details" step={{id:'synthetic-gen-details',step:'Generation details',detail:'',timestamp:0}} expandedContent={<GenerationSummary metadata={imageMetadata} onViewFullDetails={onViewFullDetails}/>}/>
</>)}
</div>)}
function StepItem({step,expandedContent}:{step:ThinkingStep;expandedContent?:ReactNode}){
const [exp,setExp]=useState(false)
const hasCont=Boolean(step.detail||expandedContent)
return(<div className="text-sm">
<button type="button" onClick={()=>hasCont&&setExp(p=>!p)} className={`flex items-center gap-2 w-full text-left ${hasCont?'hover:bg-muted/50 cursor-pointer':''} rounded px-1 py-0.5 transition-colors`}>
<CheckCircle2 className="h-3 w-3 text-success flex-shrink-0"/>
<span className="font-medium text-foreground">{step.step}</span>
{hasCont&&(exp?<ChevronDown className="h-3 w-3 text-muted-foreground ml-auto"/>:<ChevronRight className="h-3 w-3 text-muted-foreground ml-auto"/>)}
</button>
{exp&&(<div className="pl-6 pr-2 py-1">{expandedContent||(step.detail&&<div className="text-muted-foreground text-xs">{step.detail}</div>)}</div>)}
</div>)}
