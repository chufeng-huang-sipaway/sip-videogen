//AttachmentChips - Compact inline chips with thumbnails for Products, StyleReferences, and file attachments
import{useState,useEffect}from'react'
import{Package,Palette,Paperclip,X}from'lucide-react'
import{bridge,isPyWebView}from'@/lib/bridge'
import type{ProductEntry,StyleReferenceSummary,AttachedStyleReference}from'@/lib/bridge'
interface Attachment{id:string;name:string;preview?:string}
interface AttachmentChipsProps{
products:ProductEntry[]
attachedProductSlugs:string[]
onDetachProduct:(slug:string)=>void
styleReferences:StyleReferenceSummary[]
attachedStyleReferences:AttachedStyleReference[]
onDetachStyleReference:(slug:string)=>void
attachments:Attachment[]
onRemoveAttachment:(id:string)=>void}
//Product thumbnail loader
function ProductThumb({path}:{path:string}){
const[src,setSrc]=useState<string|null>(null)
useEffect(()=>{
let cancelled=false
async function load(){
if(!isPyWebView()||!path)return
try{const dataUrl=await bridge.getProductImageThumbnail(path);if(!cancelled)setSrc(dataUrl)}catch{}}
load();return()=>{cancelled=true}},[path])
if(!src)return<div className="h-5 w-5 rounded bg-muted flex items-center justify-center shrink-0"><Package className="h-3 w-3 text-muted-foreground"/></div>
return<img src={src}alt=""className="h-5 w-5 rounded object-cover shrink-0"/>}
//StyleReference thumbnail loader
function StyleRefThumb({path}:{path:string}){
const[src,setSrc]=useState<string|null>(null)
useEffect(()=>{
let cancelled=false
async function load(){
if(!isPyWebView()||!path)return
try{const dataUrl=await bridge.getStyleReferenceImageThumbnail(path);if(!cancelled)setSrc(dataUrl)}catch{}}
load();return()=>{cancelled=true}},[path])
if(!src)return<div className="h-5 w-5 rounded bg-muted flex items-center justify-center shrink-0"><Palette className="h-3 w-3 text-muted-foreground"/></div>
return<img src={src}alt=""className="h-5 w-5 rounded object-cover shrink-0"/>}
export function AttachmentChips({products,attachedProductSlugs,onDetachProduct,styleReferences,attachedStyleReferences,onDetachStyleReference,attachments,onRemoveAttachment}:AttachmentChipsProps){
const attachedProducts=products.filter(p=>attachedProductSlugs.includes(p.slug))
const missingProductSlugs=attachedProductSlugs.filter(slug=>!products.find(p=>p.slug===slug))
const hasAny=attachedProductSlugs.length>0||attachedStyleReferences.length>0||attachments.length>0
if(!hasAny)return null
return(
<div className="flex flex-wrap items-center gap-2 py-1">
{/* Product chips with thumbnail */}
{attachedProducts.map(p=>(
<div key={p.slug} className="inline-flex items-center gap-1.5 h-7 rounded-lg border border-border/50 bg-background/80 pl-1 pr-1.5 text-xs font-medium transition-all hover:border-border hover:shadow-sm">
<ProductThumb path={p.primary_image}/>
<span className="max-w-[100px] truncate">{p.name}</span>
<button type="button" onClick={()=>onDetachProduct(p.slug)} className="p-0.5 rounded text-muted-foreground/40 hover:text-destructive hover:bg-destructive/10 transition-colors"><X className="h-3 w-3"/></button>
</div>))}
{/* Missing product placeholders */}
{missingProductSlugs.map(slug=>(
<div key={slug} className="inline-flex items-center gap-1.5 h-7 rounded-lg border border-dashed border-border/50 bg-muted/30 pl-1 pr-1.5 text-xs text-muted-foreground">
<div className="h-5 w-5 rounded bg-muted/50 flex items-center justify-center shrink-0"><Package className="h-3 w-3"/></div>
<span className="max-w-[100px] truncate">{slug}</span>
<button type="button" onClick={()=>onDetachProduct(slug)} className="p-0.5 rounded hover:text-foreground transition-colors"><X className="h-3 w-3"/></button>
</div>))}
{/* StyleReference chips with thumbnail */}
{attachedStyleReferences.map(({style_reference_slug})=>{
const sr=styleReferences.find(t=>t.slug===style_reference_slug)
return(
<div key={style_reference_slug} className="inline-flex items-center gap-1.5 h-7 rounded-lg border border-border/50 bg-background/80 pl-1 pr-1.5 text-xs font-medium transition-all hover:border-border hover:shadow-sm">
{sr?.primary_image?<StyleRefThumb path={sr.primary_image}/>:<div className="h-5 w-5 rounded bg-muted flex items-center justify-center shrink-0"><Palette className="h-3 w-3 text-muted-foreground"/></div>}
<span className="max-w-[100px] truncate">{sr?.name||style_reference_slug}</span>
<button type="button" onClick={()=>onDetachStyleReference(style_reference_slug)} className="p-0.5 rounded text-muted-foreground/40 hover:text-destructive hover:bg-destructive/10 transition-colors"><X className="h-3 w-3"/></button>
</div>)})}
{/* File attachment chips */}
{attachments.map(att=>(
<div key={att.id} className="inline-flex items-center gap-1.5 h-7 rounded-lg border border-border/50 bg-background/80 pl-1 pr-1.5 text-xs font-medium transition-all hover:border-border hover:shadow-sm">
{att.preview?<img src={att.preview}alt=""className="h-5 w-5 rounded object-cover shrink-0"/>:<div className="h-5 w-5 rounded bg-muted flex items-center justify-center shrink-0"><Paperclip className="h-3 w-3 text-muted-foreground"/></div>}
<span className="max-w-[100px] truncate">{att.name}</span>
<button type="button" onClick={()=>onRemoveAttachment(att.id)} className="p-0.5 rounded text-muted-foreground/40 hover:text-destructive hover:bg-destructive/10 transition-colors"><X className="h-3 w-3"/></button>
</div>))}
</div>)}
