//GeneratorForm - form for entering prompts and starting generation
import{useState,useCallback}from'react'
import{Plus,Trash2,Play,X}from'lucide-react'
import{Button}from'@/components/ui/button'
import{Input}from'@/components/ui/input'
import{ScrollArea}from'@/components/ui/scroll-area'
interface GeneratorFormProps{
onGenerate:(prompts:string[],aspectRatio:string)=>Promise<void>
onCancel:()=>Promise<void>
isGenerating:boolean
disabled?:boolean}
const ASPECT_RATIOS=['1:1','16:9','9:16','4:3','3:4']
export function GeneratorForm({onGenerate,onCancel,isGenerating,disabled}:GeneratorFormProps){
const[prompts,setPrompts]=useState<string[]>([''])
const[aspectRatio,setAspectRatio]=useState('1:1')
const addPrompt=useCallback(()=>{setPrompts(p=>[...p,''])},[])
const removePrompt=useCallback((idx:number)=>{setPrompts(p=>p.filter((_,i)=>i!==idx))},[])
const updatePrompt=useCallback((idx:number,value:string)=>{setPrompts(p=>p.map((v,i)=>i===idx?value:v))},[])
const handleSubmit=useCallback(async()=>{
const valid=prompts.filter(p=>p.trim().length>0)
if(valid.length===0)return
await onGenerate(valid,aspectRatio)
},[prompts,aspectRatio,onGenerate])
const canSubmit=prompts.some(p=>p.trim().length>0)&&!isGenerating&&!disabled
return(<div className="flex flex-col gap-4">
<div className="flex items-center justify-between">
<h3 className="text-sm font-medium">Prompts</h3>
<Button variant="ghost" size="sm" onClick={addPrompt} disabled={isGenerating||disabled} className="gap-1.5 h-7">
<Plus className="h-3.5 w-3.5"/>Add
</Button>
</div>
<ScrollArea className="max-h-48">
<div className="flex flex-col gap-2 pr-2">
{prompts.map((prompt,idx)=>(<div key={idx} className="flex items-center gap-2">
<Input value={prompt} onChange={(e)=>updatePrompt(idx,e.target.value)} placeholder={`Prompt ${idx+1}...`} disabled={isGenerating||disabled} className="flex-1 h-9 text-sm"/>
{prompts.length>1&&(<Button variant="ghost" size="icon" onClick={()=>removePrompt(idx)} disabled={isGenerating||disabled} className="h-8 w-8 text-muted-foreground hover:text-destructive">
<Trash2 className="h-3.5 w-3.5"/>
</Button>)}
</div>))}
</div>
</ScrollArea>
<div className="flex items-center gap-2">
<span className="text-xs text-muted-foreground">Aspect:</span>
<div className="flex gap-1">
{ASPECT_RATIOS.map(ar=>(<Button key={ar} variant={aspectRatio===ar?'secondary':'ghost'} size="sm" onClick={()=>setAspectRatio(ar)} disabled={isGenerating||disabled} className="h-7 px-2 text-xs">
{ar}
</Button>))}
</div>
</div>
<div className="flex items-center gap-2 pt-2">
{isGenerating?(<Button variant="destructive" size="sm" onClick={onCancel} className="gap-1.5 flex-1">
<X className="h-3.5 w-3.5"/>Cancel
</Button>):(<Button size="sm" onClick={handleSubmit} disabled={!canSubmit} className="gap-1.5 flex-1">
<Play className="h-3.5 w-3.5"/>Generate
</Button>)}
</div>
</div>)}
