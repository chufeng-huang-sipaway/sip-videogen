import { useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { bridge } from '@/lib/bridge'
import type { Interaction } from '@/lib/bridge'
import { cn } from '@/lib/utils'
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
return null}
