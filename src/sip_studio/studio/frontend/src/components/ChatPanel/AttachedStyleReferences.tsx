import {useState,useEffect} from 'react'
import {Layout,X} from 'lucide-react'
import {bridge,isPyWebView,type StyleReferenceSummary,type AttachedStyleReference} from '@/lib/bridge'
interface AttachedStyleReferencesProps {
styleReferences:StyleReferenceSummary[]
attachedStyleReferences:AttachedStyleReference[]
onDetach:(slug:string)=>void}
function StyleReferenceThumbnail({path}:{path:string}){
const [src,setSrc]=useState<string|null>(null)
useEffect(()=>{
let cancelled=false
async function load(){
if(!isPyWebView()||!path)return
try{const dataUrl=await bridge.getStyleReferenceImageThumbnail(path);if(!cancelled)setSrc(dataUrl)}catch{}}
load()
return()=>{cancelled=true}},[path])
if(!src){return(<div className="h-8 w-8 rounded bg-muted flex items-center justify-center shrink-0"><Layout className="h-4 w-4 text-muted-foreground"/></div>)}
return<img src={src}alt=""className="h-8 w-8 rounded object-cover shrink-0"/>}
export function AttachedStyleReferences({styleReferences,attachedStyleReferences,onDetach}:AttachedStyleReferencesProps){
if(attachedStyleReferences.length===0)return null
return(
<div className="px-4 py-2 border-t border-border/40 bg-muted/40 backdrop-blur-sm">
<div className="flex items-center gap-2 text-xs font-medium text-muted-foreground mb-2">
<Layout className="h-3 w-3"/>
<span>Style</span>
</div>
<div className="flex flex-wrap gap-2">
{attachedStyleReferences.map(({style_reference_slug})=>{
const sr=styleReferences.find(t=>t.slug===style_reference_slug)
return(
<div key={style_reference_slug}className="flex items-center gap-2 rounded-lg border border-border/60 bg-background/80 px-2 py-1 shadow-sm transition-all hover:shadow-md hover:border-border">
{sr?.primary_image?(<StyleReferenceThumbnail path={sr.primary_image}/>):(<div className="h-8 w-8 rounded bg-muted flex items-center justify-center shrink-0"><Layout className="h-4 w-4 text-muted-foreground/50"/></div>)}
<div className="text-xs max-w-[120px] truncate font-medium">{sr?.name||style_reference_slug}</div>
<button type="button"className="text-muted-foreground/60 hover:text-destructive transition-colors"onClick={()=>onDetach(style_reference_slug)}title="Remove">
<X className="h-3 w-3"/>
</button>
</div>)})}
</div>
</div>)}
