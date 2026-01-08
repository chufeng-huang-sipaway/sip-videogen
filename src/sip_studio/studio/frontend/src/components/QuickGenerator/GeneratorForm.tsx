//GeneratorForm - form for entering prompts and starting generation
import{useState,useCallback}from'react'
import{Play,X}from'lucide-react'
import{Button}from'@/components/ui/button'
import{Input}from'@/components/ui/input'
export interface Product{slug:string;name:string}
export interface StyleReference{slug:string;name:string}
interface GeneratorFormProps{
onGenerate:(prompts:string[],aspectRatio:string,productSlug?:string,styleRefSlug?:string)=>Promise<void>
onCancel:()=>Promise<void>
isGenerating:boolean
disabled?:boolean
products?:Product[]
styleReferences?:StyleReference[]}
const ASPECT_RATIOS=['1:1','16:9','9:16','4:3','3:4']
const COUNT_OPTIONS=[1,3,5,10]
export function GeneratorForm({onGenerate,onCancel,isGenerating,disabled,products=[],styleReferences=[]}:GeneratorFormProps){
const[prompt,setPrompt]=useState('')
const[count,setCount]=useState(1)
const[aspectRatio,setAspectRatio]=useState('1:1')
const[productSlug,setProductSlug]=useState<string|undefined>()
const[styleRefSlug,setStyleRefSlug]=useState<string|undefined>()
const handleSubmit=useCallback(async()=>{
if(!prompt.trim())return
//Generate count copies of the same prompt
const prompts=Array(count).fill(prompt.trim())
await onGenerate(prompts,aspectRatio,productSlug,styleRefSlug)
},[prompt,count,aspectRatio,productSlug,styleRefSlug,onGenerate])
const canSubmit=prompt.trim().length>0&&!isGenerating&&!disabled
return(<div className="flex flex-col gap-4">
{/*Prompt input*/}
<div className="flex flex-col gap-2">
<h3 className="text-sm font-medium">Prompt</h3>
<Input value={prompt} onChange={(e)=>setPrompt(e.target.value)} placeholder="Describe your image..." disabled={isGenerating||disabled} className="h-9 text-sm"/>
</div>
{/*Product dropdown*/}
{products.length>0&&(<div className="flex items-center gap-2">
<span className="text-xs text-muted-foreground w-16">Product:</span>
<select value={productSlug||''} onChange={(e)=>setProductSlug(e.target.value||undefined)} disabled={isGenerating||disabled} className="flex-1 h-8 text-xs px-2 rounded-md border border-input bg-background">
<option value="">None</option>
{products.map(p=>(<option key={p.slug} value={p.slug}>{p.name}</option>))}
</select>
</div>)}
{/*Style Reference dropdown*/}
{styleReferences.length>0&&(<div className="flex items-center gap-2">
<span className="text-xs text-muted-foreground w-16">Style:</span>
<select value={styleRefSlug||''} onChange={(e)=>setStyleRefSlug(e.target.value||undefined)} disabled={isGenerating||disabled} className="flex-1 h-8 text-xs px-2 rounded-md border border-input bg-background">
<option value="">None</option>
{styleReferences.map(s=>(<option key={s.slug} value={s.slug}>{s.name}</option>))}
</select>
</div>)}
{/*Count selector*/}
<div className="flex items-center gap-2">
<span className="text-xs text-muted-foreground w-16">Count:</span>
<div className="flex gap-1">
{COUNT_OPTIONS.map(c=>(<Button key={c} variant={count===c?'secondary':'ghost'} size="sm" onClick={()=>setCount(c)} disabled={isGenerating||disabled} className="h-7 w-8 px-0 text-xs">
{c}
</Button>))}
</div>
</div>
{/*Aspect ratio selector*/}
<div className="flex items-center gap-2">
<span className="text-xs text-muted-foreground w-16">Aspect:</span>
<div className="flex gap-1">
{ASPECT_RATIOS.map(ar=>(<Button key={ar} variant={aspectRatio===ar?'secondary':'ghost'} size="sm" onClick={()=>setAspectRatio(ar)} disabled={isGenerating||disabled} className="h-7 px-2 text-xs">
{ar}
</Button>))}
</div>
</div>
{/*Generate/Cancel button*/}
<div className="flex items-center gap-2 pt-2">
{isGenerating?(<Button variant="destructive" size="sm" onClick={onCancel} className="gap-1.5 flex-1">
<X className="h-3.5 w-3.5"/>Cancel
</Button>):(<Button size="sm" onClick={handleSubmit} disabled={!canSubmit} className="gap-1.5 flex-1">
<Play className="h-3.5 w-3.5"/>Generate {count>1?`(${count})`:''}</Button>)}
</div>
</div>)}
