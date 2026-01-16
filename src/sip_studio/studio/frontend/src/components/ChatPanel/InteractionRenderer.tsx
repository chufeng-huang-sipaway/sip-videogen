import { useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { bridge, type ClarificationResponse } from '@/lib/bridge'
import type { Interaction, DeepResearchClarification } from '@/lib/bridge'
import { cn } from '@/lib/utils'
import { Telescope } from 'lucide-react'
interface Props {interaction:Interaction;onSelect:(selection:string)=>void;disabled?:boolean}
export function InteractionRenderer({interaction,onSelect,disabled}:Props){
const[cv,setCv]=useState('')
const[imgPrev,setImgPrev]=useState<Record<string,string>>({})
const reqPrev=useRef<Set<string>>(new Set())
useEffect(()=>{if(interaction.type!=='image_select')return;for(const p of interaction.image_paths){if(reqPrev.current.has(p))continue;reqPrev.current.add(p);bridge.getAssetThumbnail(p).then((d)=>{setImgPrev(pr=>(pr[p]?pr:{...pr,[p]:d}))}).catch((e)=>{reqPrev.current.delete(p);console.error('Failed to load preview:',e)})}},[interaction])
if(interaction.type==='choices'){return(
<div className="mt-4 w-full">
<div className="rounded-xl border border-border bg-card p-4 space-y-3 shadow-sm">
<p className="text-sm text-foreground leading-relaxed">{interaction.question}</p>
<div className="flex flex-col gap-2">
{interaction.choices.map((c,i)=>(<Button key={c} variant={i===0?"default":"outline"} size="sm" onClick={()=>onSelect(c)} disabled={disabled} className={cn("w-full justify-start text-left whitespace-normal h-auto py-2.5 px-4",i===0&&"font-medium")}>{c}</Button>))}
</div>
{interaction.allow_custom&&(<div className="flex gap-2 pt-1">
<Input placeholder="Or type something else..." value={cv} onChange={(e)=>setCv(e.target.value)} disabled={disabled} className="text-sm" onKeyDown={(e)=>{if(e.key==='Enter'&&cv.trim())onSelect(cv)}}/>
<Button size="sm" onClick={()=>onSelect(cv)} disabled={disabled||!cv.trim()}>Send</Button>
</div>)}
</div>
</div>)}
if(interaction.type==='image_select'){return(
<div className="mt-4 w-full">
<div className="rounded-xl border border-border bg-card p-4 space-y-3 shadow-sm">
<p className="text-sm text-foreground leading-relaxed">{interaction.question}</p>
<div className="grid grid-cols-2 gap-2">
{interaction.image_paths.map((p,i)=>(<button key={p} onClick={()=>onSelect(`Option ${i+1}: ${interaction.labels[i]}`)} disabled={disabled} className="relative group border border-border rounded-lg overflow-hidden hover:ring-2 hover:ring-primary/50 hover:border-primary/50 disabled:opacity-50 text-left transition-all">
{imgPrev[p]?(<img src={imgPrev[p]} alt={interaction.labels[i]} className="w-full h-32 object-cover"/>):(<div className="w-full h-32 bg-muted flex items-center justify-center"><span className="text-muted-foreground text-xs">Loading...</span></div>)}
<div className="absolute bottom-0 left-0 right-0 bg-black/70 text-white text-xs py-1.5 px-2">{interaction.labels[i]}</div>
</button>))}
</div>
</div>
</div>)}
if(interaction.type==='deep_research_clarification'){return(<ClarificationPanel interaction={interaction} onSubmit={(resp)=>{
  bridge.executeDeepResearch(resp,interaction.query).then(r=>{onSelect(`__research_started__:${r.response_id}:${interaction.query}`)}).catch(e=>onSelect(`__research_error__:${e.message}`))
}} onCancel={()=>onSelect('__cancelled__')} disabled={disabled}/>)}
return null}
//ClarificationPanel component for deep research confirmation
function ClarificationPanel({interaction,onSubmit,onCancel,disabled}:{interaction:DeepResearchClarification;onSubmit:(response:ClarificationResponse)=>void;onCancel:()=>void;disabled?:boolean}){
const[answers,setAnswers]=useState<Record<string,string>>({})
const[submitting,setSubmitting]=useState(false)
const handleSubmit=()=>{if(submitting)return;setSubmitting(true);onSubmit({answers,confirmed:true})}
const allAnswered=interaction.questions.every(q=>answers[q.id]&&answers[q.id].trim().length>0)
return(
<div className="mt-4 w-full">
<div className="rounded-xl border border-border bg-card p-4 space-y-4 shadow-soft">
{/* Header */}
<div className="flex items-center gap-2">
<Telescope className="h-5 w-5 text-brand-500"/>
<span className="font-medium">Deep Research</span>
</div>
{/* Context summary */}
<p className="text-sm text-muted-foreground">{interaction.contextSummary}</p>
{/* Questions */}
{interaction.questions.map(q=>(<div key={q.id} className="space-y-2">
<p className="text-sm font-medium">{q.question}</p>
<div className="flex flex-col gap-1.5">
{q.options.map(opt=>(<label key={opt.value} className={cn("flex items-center gap-2 p-2 rounded-lg border cursor-pointer transition-colors",answers[q.id]===opt.value&&"border-brand-500 bg-brand-500/10",opt.recommended&&"ring-1 ring-brand-500/30",disabled&&"opacity-50 cursor-not-allowed")}>
<input type="radio" name={q.id} value={opt.value} checked={answers[q.id]===opt.value} onChange={()=>setAnswers(a=>({...a,[q.id]:opt.value}))} disabled={disabled||submitting} className="accent-brand-500"/>
<span className="text-sm">{opt.label}</span>
{opt.recommended&&<span className="text-xs text-brand-500">(Recommended)</span>}
</label>))}
{q.allowCustom&&(<Input placeholder="Or type your own..." value={answers[q.id]?.startsWith('custom:')?answers[q.id].slice(7):''} onChange={e=>setAnswers(a=>({...a,[q.id]:e.target.value?`custom:${e.target.value}`:''}))} disabled={disabled||submitting} className="text-sm"/>)}
</div>
</div>))}
{/* Footer */}
<div className="flex items-center justify-between pt-2 border-t border-border/50">
<span className="text-xs text-muted-foreground">⏱ {interaction.estimatedDuration}</span>
<div className="flex gap-2">
<Button variant="ghost" size="sm" onClick={onCancel} disabled={disabled||submitting}>Cancel</Button>
<Button size="sm" onClick={handleSubmit} disabled={disabled||submitting||!allAnswered}>{submitting?'Starting...':'Start Research'}</Button>
</div>
</div>
</div>
</div>)}
