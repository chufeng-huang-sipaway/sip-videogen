import {useState,useEffect} from 'react'
import {Layout,X,Lock,Unlock} from 'lucide-react'
import {bridge,isPyWebView,type TemplateSummary,type AttachedTemplate} from '@/lib/bridge'
interface AttachedTemplatesProps {
templates:TemplateSummary[]
attachedTemplates:AttachedTemplate[]
onDetach:(slug:string)=>void
onToggleStrict:(slug:string,strict:boolean)=>void}
function TemplateThumbnail({path}:{path:string}){
const [src,setSrc]=useState<string|null>(null)
useEffect(()=>{
let cancelled=false
async function load(){
if(!isPyWebView()||!path)return
try{const dataUrl=await bridge.getTemplateImageThumbnail(path);if(!cancelled)setSrc(dataUrl)}catch{}}
load()
return()=>{cancelled=true}},[path])
if(!src){return(<div className="h-8 w-8 rounded bg-gray-200 dark:bg-gray-700 flex items-center justify-center shrink-0"><Layout className="h-4 w-4 text-gray-400"/></div>)}
return<img src={src}alt=""className="h-8 w-8 rounded object-cover shrink-0"/>}
export function AttachedTemplates({templates,attachedTemplates,onDetach,onToggleStrict}:AttachedTemplatesProps){
if(attachedTemplates.length===0)return null
return(
<div className="px-4 py-2 border-t border-border/40 bg-muted/40 backdrop-blur-sm">
<div className="flex items-center gap-2 text-xs font-medium text-muted-foreground mb-2">
<Layout className="h-3 w-3"/>
<span>Templates attached to chat</span>
</div>
<div className="flex flex-wrap gap-2">
{attachedTemplates.map(({template_slug,strict})=>{
const template=templates.find(t=>t.slug===template_slug)
return(
<div key={template_slug}className="flex items-center gap-2 rounded-lg border border-border/60 bg-background/80 px-2 py-1 shadow-sm transition-all hover:shadow-md hover:border-border">
{template?.primary_image?(<TemplateThumbnail path={template.primary_image}/>):(<div className="h-8 w-8 rounded bg-muted flex items-center justify-center shrink-0"><Layout className="h-4 w-4 text-muted-foreground/50"/></div>)}
<div className="text-xs max-w-[120px] truncate font-medium">{template?.name||template_slug}</div>
<button type="button"className={`p-1 rounded transition-colors ${strict?'text-brand-500 hover:text-brand-600 bg-brand-a10':'text-muted-foreground/60 hover:text-muted-foreground'}`}onClick={()=>onToggleStrict(template_slug,!strict)}title={strict?'Strict mode ON - click to allow variation':'Loose mode - click to enforce strict layout'}>
{strict?<Lock className="h-3 w-3"/>:<Unlock className="h-3 w-3"/>}
</button>
<button type="button"className="text-muted-foreground/60 hover:text-destructive transition-colors"onClick={()=>onDetach(template_slug)}title="Remove from chat">
<X className="h-3 w-3"/>
</button>
</div>)})}
</div>
</div>)}
