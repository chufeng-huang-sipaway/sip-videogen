//TemplateDetailView for displaying full template details with analysis
import{useState,useEffect,useCallback}from'react'
import{Layout,Star,Loader2,RefreshCw,Pencil,Trash2,Lock,Unlock,X,ChevronDown,ChevronRight}from'lucide-react'
import{Button}from'@/components/ui/button'
import{Alert,AlertDescription}from'@/components/ui/alert'
import{useTemplates}from'@/context/TemplateContext'
import{bridge,isPyWebView,type TemplateFull,type TemplateAnalysis,type TemplateAnalysisV1,type TemplateAnalysisV2,isV2Analysis}from'@/lib/bridge'
import{toast}from'@/components/ui/toaster'
interface TemplateDetailViewProps{
templateSlug:string
onEdit:()=>void
onDelete:()=>void
onClose?:()=>void}
//Thumbnail component
function Thumbnail({path,size='md'}:{path:string;size?:'sm'|'md'|'lg'}){
const[src,setSrc]=useState<string|null>(null)
useEffect(()=>{let c=false
async function load(){if(!isPyWebView()||!path)return
try{const url=size==='sm'?await bridge.getTemplateImageThumbnail(path):await bridge.getTemplateImageFull(path)
if(!c)setSrc(url)}catch{}}
load();return()=>{c=true}},[path,size])
const sz=size==='lg'?'h-32 w-32':size==='md'?'h-24 w-24':'h-12 w-12'
if(!src)return(<div className={`${sz} rounded bg-gray-200 dark:bg-gray-700 flex items-center justify-center shrink-0`}><Loader2 className="h-4 w-4 text-gray-400 animate-spin"/></div>)
return<img src={src} alt="" className={`${sz} rounded object-cover shrink-0`}/>}
//Collapsible section
function DetailSection({title,defaultOpen=false,children}:{title:string;defaultOpen?:boolean;children:React.ReactNode}){
const[open,setOpen]=useState(defaultOpen)
return(<div className="border-b border-border/50 last:border-b-0">
<button className="flex items-center gap-2 w-full py-2 px-1 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors" onClick={()=>setOpen(!open)}>
{open?<ChevronDown className="h-3 w-3"/>:<ChevronRight className="h-3 w-3"/>}
{title}
</button>
{open&&<div className="pb-3 px-1">{children}</div>}
</div>)}
//Analysis summary component - handles both V1 and V2
function AnalysisSummary({analysis}:{analysis:TemplateAnalysis}){
if(isV2Analysis(analysis))return<AnalysisSummaryV2 analysis={analysis}/>
return<AnalysisSummaryV1 analysis={analysis as TemplateAnalysisV1}/>}
//V2 Analysis display (semantic)
function AnalysisSummaryV2({analysis}:{analysis:TemplateAnalysisV2}){
const{canvas,style,layout,copywriting,visual_scene,constraints}=analysis
return(<div className="space-y-1.5">
<div className="text-xs font-medium text-primary mb-2">V2 Semantic Analysis</div>
<DetailSection title="Layout" defaultOpen={true}>
<div className="space-y-1 text-xs">
<div><span className="text-muted-foreground">Structure: </span><span className="font-medium">{layout.structure}</span></div>
{layout.hierarchy&&<div><span className="text-muted-foreground">Hierarchy: </span><span>{layout.hierarchy}</span></div>}
{layout.alignment&&<div><span className="text-muted-foreground">Alignment: </span><span>{layout.alignment}</span></div>}
{layout.zones.length>0&&<div><span className="text-muted-foreground">Zones: </span><span>{layout.zones.join(', ')}</span></div>}
</div>
</DetailSection>
<DetailSection title={`Copywriting (${copywriting.benefits.length} benefits)`} defaultOpen={true}>
<div className="space-y-1 text-xs">
{copywriting.headline&&<div><span className="text-muted-foreground">Headline: </span><span className="font-medium">"{copywriting.headline}"</span></div>}
{copywriting.subheadline&&<div><span className="text-muted-foreground">Subheadline: </span><span>"{copywriting.subheadline}"</span></div>}
{copywriting.benefits.length>0&&(<div className="space-y-0.5"><span className="text-muted-foreground">Benefits:</span>
{copywriting.benefits.slice(0,5).map((b,i)=>(<div key={i} className="pl-2 truncate">• {b}</div>))}
{copywriting.benefits.length>5&&<div className="pl-2 text-muted-foreground">+{copywriting.benefits.length-5} more</div>}
</div>)}
{copywriting.cta&&<div><span className="text-muted-foreground">CTA: </span><span>"{copywriting.cta}"</span></div>}
{copywriting.disclaimer&&<div className="truncate"><span className="text-muted-foreground">Disclaimer: </span><span className="text-[10px]">{copywriting.disclaimer.slice(0,50)}...</span></div>}
</div>
</DetailSection>
<DetailSection title="Visual Scene">
<div className="space-y-1 text-xs">
{visual_scene.scene_description&&<div><span className="text-muted-foreground">Scene: </span><span>{visual_scene.scene_description}</span></div>}
{visual_scene.product_placement&&<div><span className="text-muted-foreground">Product: </span><span>{visual_scene.product_placement}</span></div>}
{visual_scene.photography_style&&<div><span className="text-muted-foreground">Style: </span><span>{visual_scene.photography_style}</span></div>}
{visual_scene.visual_treatments.length>0&&<div><span className="text-muted-foreground">Treatments: </span><span>{visual_scene.visual_treatments.join(', ')}</span></div>}
</div>
</DetailSection>
<DetailSection title="Style">
<div className="space-y-1 text-xs">
<div><span className="text-muted-foreground">Mood: </span><span>{style.mood}</span></div>
<div><span className="text-muted-foreground">Lighting: </span><span>{style.lighting}</span></div>
{style.palette.length>0&&(<div className="flex items-center gap-1.5">
<span className="text-muted-foreground">Palette:</span>
{style.palette.slice(0,5).map((c,i)=>(<div key={i} className="h-3 w-3 rounded-sm border border-border/50" style={{backgroundColor:c}} title={c}/>))}
</div>)}
</div>
</DetailSection>
{constraints.non_negotiables.length>0&&(<DetailSection title="Non-Negotiables">
<div className="space-y-0.5 text-xs">
{constraints.non_negotiables.slice(0,4).map((n,i)=>(<div key={i} className="truncate">• {n}</div>))}
</div>
</DetailSection>)}
<div className="text-xs text-muted-foreground mt-2">Canvas: {canvas.aspect_ratio}</div>
</div>)}
//V1 Analysis display (geometry, deprecated)
function AnalysisSummaryV1({analysis}:{analysis:TemplateAnalysisV1}){
const{canvas,style,elements,product_slot,message}=analysis
return(<div className="space-y-1.5">
<div className="text-xs font-medium text-amber-500 mb-2">V1 Analysis (legacy)</div>
<DetailSection title="Canvas" defaultOpen={true}>
<div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
<span className="text-muted-foreground">Aspect:</span><span className="font-medium">{canvas.aspect_ratio}</span>
<span className="text-muted-foreground">Background:</span><span className="font-medium truncate">{canvas.background}</span>
</div>
</DetailSection>
<DetailSection title="Message">
<div className="space-y-1 text-xs">
<div><span className="text-muted-foreground">Intent: </span><span>{message.intent}</span></div>
<div><span className="text-muted-foreground">Audience: </span><span>{message.audience}</span></div>
{message.key_claims.length>0&&(<div><span className="text-muted-foreground">Claims: </span><span>{message.key_claims.join(', ')}</span></div>)}
</div>
</DetailSection>
<DetailSection title="Style">
<div className="space-y-1 text-xs">
<div><span className="text-muted-foreground">Mood: </span><span>{style.mood}</span></div>
<div><span className="text-muted-foreground">Lighting: </span><span>{style.lighting}</span></div>
{style.palette.length>0&&(<div className="flex items-center gap-1.5">
<span className="text-muted-foreground">Palette:</span>
{style.palette.slice(0,5).map((c,i)=>(<div key={i} className="h-3 w-3 rounded-sm border border-border/50" style={{backgroundColor:c}} title={c}/>))}
</div>)}
</div>
</DetailSection>
<DetailSection title={`Elements (${elements.length})`}>
<div className="space-y-1">
{elements.slice(0,6).map(el=>(<div key={el.id} className="flex items-center gap-2 text-xs">
<span className="w-16 truncate font-mono text-muted-foreground">{el.type}</span>
<span className="flex-1 truncate">{el.role}</span>
</div>))}
{elements.length>6&&<div className="text-xs text-muted-foreground">+{elements.length-6} more</div>}
</div>
</DetailSection>
{product_slot&&(<DetailSection title="Product Slot">
<div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
<span className="text-muted-foreground">ID:</span><span className="font-mono">{product_slot.id}</span>
<span className="text-muted-foreground">Mode:</span><span>{product_slot.interaction.replacement_mode}</span>
</div>
</DetailSection>)}
</div>)}
export function TemplateDetailView({templateSlug,onEdit,onDelete,onClose}:TemplateDetailViewProps){
const{getTemplate,getTemplateImages,reanalyzeTemplate,deleteTemplate}=useTemplates()
const[template,setTemplate]=useState<TemplateFull|null>(null)
const[images,setImages]=useState<string[]>([])
const[isLoading,setIsLoading]=useState(true)
const[isReanalyzing,setIsReanalyzing]=useState(false)
const[error,setError]=useState<string|null>(null)
const load=useCallback(async()=>{setIsLoading(true);setError(null)
try{const[t,imgs]=await Promise.all([getTemplate(templateSlug),getTemplateImages(templateSlug)])
setTemplate(t);setImages(imgs)
}catch(err){setError(err instanceof Error?err.message:'Failed to load template')
}finally{setIsLoading(false)}},[templateSlug,getTemplate,getTemplateImages])
useEffect(()=>{load()},[load])
const handleReanalyze=async()=>{if(isReanalyzing)return
setIsReanalyzing(true);setError(null)
try{await reanalyzeTemplate(templateSlug)
await load()
toast.success('Template re-analyzed successfully')
}catch(err){const msg=err instanceof Error?err.message:'Re-analysis failed';setError(msg);toast.error(msg)
}finally{setIsReanalyzing(false)}}
const handleDelete=async()=>{if(!confirm(`Delete template "${template?.name}"? This cannot be undone.`))return
try{await deleteTemplate(templateSlug);onDelete()
}catch(err){toast.error(err instanceof Error?err.message:'Delete failed')}}
if(isLoading)return(<div className="p-4 flex items-center gap-2 text-sm text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin"/>Loading template...</div>)
if(error&&!template)return(<div className="p-4"><Alert variant="destructive"><AlertDescription className="flex items-center justify-between"><span>{error}</span><Button variant="ghost" size="sm" onClick={load}>Retry</Button></AlertDescription></Alert></div>)
if(!template)return null
return(<div className="space-y-4 p-4">
{/*Header*/}
<div className="flex items-start gap-3">
<div className="p-2 rounded-lg bg-indigo-500/10"><Layout className="h-5 w-5 text-indigo-500"/></div>
<div className="flex-1 min-w-0">
<div className="flex items-center gap-2">
<h3 className="font-semibold text-base truncate">{template.name}</h3>
{template.default_strict?<span title="Strict by default"><Lock className="h-3.5 w-3.5 text-primary"/></span>:<span title="Loose by default"><Unlock className="h-3.5 w-3.5 text-amber-500"/></span>}
</div>
{template.description&&<p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{template.description}</p>}
</div>
{onClose&&<Button variant="ghost" size="icon" className="h-7 w-7 shrink-0" onClick={onClose}><X className="h-4 w-4"/></Button>}
</div>
{/*Error alert*/}
{error&&<Alert variant="destructive" className="py-2"><AlertDescription className="text-xs">{error}</AlertDescription></Alert>}
{/*Images*/}
{images.length>0&&(<div className="space-y-1.5">
<span className="text-xs font-medium text-muted-foreground">Images</span>
<div className="flex flex-wrap gap-2">
{images.map((path)=>(<div key={path} className={`relative rounded-md overflow-hidden ${path===template.primary_image?'ring-2 ring-primary ring-offset-2':''}`}>
<Thumbnail path={path} size="md"/>
{path===template.primary_image&&(<div className="absolute top-1 left-1 bg-primary text-primary-foreground rounded-full p-0.5 shadow-sm"><Star className="h-2.5 w-2.5 fill-current"/></div>)}
</div>))}
</div>
</div>)}
{/*Analysis*/}
<div className="space-y-1.5">
<div className="flex items-center justify-between">
<span className="text-xs font-medium text-muted-foreground">Analysis</span>
<Button variant="ghost" size="sm" className="h-6 px-2 text-xs" onClick={handleReanalyze} disabled={isReanalyzing}>
{isReanalyzing?<><Loader2 className="h-3 w-3 mr-1 animate-spin"/>Analyzing...</>:<><RefreshCw className="h-3 w-3 mr-1"/>Re-analyze</>}
</Button>
</div>
{template.analysis?<AnalysisSummary analysis={template.analysis}/>:(<div className="py-3 text-xs text-muted-foreground italic bg-muted/50 rounded px-2">No analysis available. Click Re-analyze to generate.</div>)}
</div>
{/*Actions*/}
<div className="flex items-center gap-2 pt-2 border-t border-border/50">
<Button variant="outline" size="sm" className="flex-1" onClick={onEdit}><Pencil className="h-3.5 w-3.5 mr-1.5"/>Edit</Button>
<Button variant="outline" size="sm" className="flex-1 text-red-600 hover:text-red-700 hover:bg-red-50" onClick={handleDelete}><Trash2 className="h-3.5 w-3.5 mr-1.5"/>Delete</Button>
</div>
{/*Meta*/}
<div className="text-[10px] text-muted-foreground/70 space-y-0.5">
<div>Created: {new Date(template.created_at).toLocaleDateString()}</div>
<div>Updated: {new Date(template.updated_at).toLocaleDateString()}</div>
</div>
</div>)}
