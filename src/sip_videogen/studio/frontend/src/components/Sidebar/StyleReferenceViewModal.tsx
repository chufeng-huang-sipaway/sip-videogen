//StyleReferenceViewModal - View-first modal for style reference analysis
import{useState,useEffect,useCallback}from'react'
import{Layout,Loader2,Check,Circle,Lock,Unlock,Pencil,Trash2}from'lucide-react'
import{Button}from'@/components/ui/button'
import{Dialog,DialogContent,DialogHeader,DialogTitle}from'@/components/ui/dialog'
import{useStyleReferences}from'@/context/StyleReferenceContext'
import{bridge,isPyWebView,isV2StyleReferenceAnalysis}from'@/lib/bridge'
import type{StyleReferenceFull,StyleReferenceAnalysisV2}from'@/lib/bridge'
interface StyleReferenceViewModalProps{open:boolean;onOpenChange:(open:boolean)=>void;styleRefSlug:string;onEdit?:(slug:string)=>void;onDelete?:(slug:string)=>void}
//Info row for label-value pairs
function InfoRow({label,value}:{label:string;value:string|undefined|null}){
if(!value)return null
return(<div className="flex justify-between gap-2"><span className="text-xs text-neutral-500 dark:text-neutral-400 shrink-0">{label}</span><span className="text-sm text-neutral-900 dark:text-neutral-100 text-right">{value}</span></div>)}
//Color swatch component
function ColorSwatch({color}:{color:string}){return(<div className="w-7 h-7 rounded-md border border-neutral-200 dark:border-neutral-700 shadow-sm" style={{backgroundColor:color}} title={color}/>)}
//Section wrapper
function Section({title,children}:{title:string;children:React.ReactNode}){return(<div className="space-y-2"><h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">{title}</h3>{children}</div>)}
//Card wrapper for info content
function InfoCard({children}:{children:React.ReactNode}){return(<div className="bg-neutral-100 dark:bg-neutral-800 rounded-md p-3 space-y-1.5">{children}</div>)}
export function StyleReferenceViewModal({open,onOpenChange,styleRefSlug,onEdit,onDelete}:StyleReferenceViewModalProps){
const{getStyleReference,attachStyleReference,detachStyleReference,setStyleReferenceStrictness,attachedStyleReferences}=useStyleReferences()
const[styleRef,setStyleRef]=useState<StyleReferenceFull|null>(null)
const[imageSrc,setImageSrc]=useState<string|null>(null)
const[isLoading,setIsLoading]=useState(true)
const[error,setError]=useState<string|null>(null)
//Check if attached
const attached=attachedStyleReferences.find(a=>a.style_reference_slug===styleRefSlug)
const isAttached=!!attached
const isStrict=attached?.strict??false
//Load style reference data
useEffect(()=>{if(!open||!styleRefSlug)return
let cancelled=false
async function load(){setIsLoading(true);setError(null);setImageSrc(null)
try{const sr=await getStyleReference(styleRefSlug)
if(cancelled)return
setStyleRef(sr)
//Load full image
if(isPyWebView()&&sr.primary_image){try{const url=await bridge.getStyleReferenceImageFull(sr.primary_image);if(!cancelled)setImageSrc(url)}catch{}}}
catch(err){if(!cancelled)setError(err instanceof Error?err.message:'Failed to load')}
finally{if(!cancelled)setIsLoading(false)}}
load();return()=>{cancelled=true}},[open,styleRefSlug,getStyleReference])
const handleClose=useCallback(()=>onOpenChange(false),[onOpenChange])
const handleAttach=()=>{attachStyleReference(styleRefSlug)}
const handleDetach=()=>{detachStyleReference(styleRefSlug)}
const handleToggleStrict=()=>{setStyleReferenceStrictness(styleRefSlug,!isStrict)}
const handleEdit=()=>{handleClose();onEdit?.(styleRefSlug)}
const handleDelete=()=>{if(confirm(`Delete style reference "${styleRef?.name}"? This cannot be undone.`)){handleClose();onDelete?.(styleRefSlug)}}
//Get V2 analysis if available
const analysis=styleRef?.analysis
const v2=analysis&&isV2StyleReferenceAnalysis(analysis)?analysis as StyleReferenceAnalysisV2:null
return(<Dialog open={open} onOpenChange={onOpenChange}><DialogContent className="max-w-3xl max-h-[85vh] overflow-hidden"><DialogHeader><DialogTitle className="flex items-center gap-2"><Layout className="h-5 w-5 text-brand-500"/>{styleRef?.name||'Style Reference'}</DialogTitle></DialogHeader>
{isLoading?(<div className="flex items-center justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-brand-500"/></div>):error?(<div className="text-sm text-destructive py-4">{error}</div>):(
<div className="grid grid-cols-[260px_1fr] gap-6">
{/*Left Column - Image & Actions*/}
<div className="space-y-4">
{/*Reference Image*/}
<div className="aspect-square rounded-lg overflow-hidden bg-neutral-100 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700">
{imageSrc?(<img src={imageSrc} alt={styleRef?.name} className="w-full h-full object-cover"/>):(<div className="w-full h-full flex items-center justify-center"><Layout className="h-12 w-12 text-neutral-400"/></div>)}</div>
{/*Aspect Ratio Badge*/}
{analysis?.canvas?.aspect_ratio&&(<div className="flex items-center gap-2"><span className="text-xs text-neutral-500 dark:text-neutral-400">Aspect Ratio:</span><span className="text-sm font-medium text-neutral-900 dark:text-neutral-100">{analysis.canvas.aspect_ratio}</span></div>)}
{/*Attach Controls*/}
<div className="space-y-2">
{isAttached?(<><Button variant="outline" size="sm" className="w-full justify-start gap-2" onClick={handleToggleStrict}>{isStrict?<><Lock className="h-4 w-4 text-brand-500"/>Strictly Following</>:<><Unlock className="h-4 w-4"/>Allow Variation</>}</Button>
<Button variant="ghost" size="sm" className="w-full justify-start text-neutral-500" onClick={handleDetach}>Detach from Chat</Button></>):(<Button variant="default" size="sm" className="w-full bg-brand-500 hover:bg-brand-600" onClick={handleAttach}>Attach to Chat</Button>)}</div>
{/*Edit & Delete*/}
<div className="flex gap-2 pt-2 border-t border-neutral-200 dark:border-neutral-700">
<Button variant="outline" size="sm" className="flex-1 gap-1.5" onClick={handleEdit}><Pencil className="h-3.5 w-3.5"/>Edit</Button>
<Button variant="outline" size="sm" className="text-destructive hover:text-destructive hover:bg-destructive/10 gap-1.5" onClick={handleDelete}><Trash2 className="h-3.5 w-3.5"/>Delete</Button></div>
</div>
{/*Right Column - Analysis*/}
<div className="space-y-4 overflow-y-auto max-h-[60vh] pr-2">
{v2?(<>
{/*Visual Style Section*/}
<Section title="Visual Style"><InfoCard>
<InfoRow label="Mood" value={v2.style?.mood}/>
<InfoRow label="Lighting" value={v2.style?.lighting}/>
<InfoRow label="Photography" value={v2.visual_scene?.photography_style}/>
{v2.style?.materials?.length>0&&(<div className="pt-1"><span className="text-xs text-neutral-500 dark:text-neutral-400">Materials:</span><p className="text-sm text-neutral-900 dark:text-neutral-100 mt-0.5">{v2.style.materials.join(' • ')}</p></div>)}
</InfoCard></Section>
{/*Color Palette*/}
{v2.style?.palette?.length>0&&(<Section title="Color Palette"><div className="flex gap-2 flex-wrap">{v2.style.palette.map((c,i)=><ColorSwatch key={i} color={c}/>)}</div></Section>)}
{/*Composition*/}
<Section title="Composition"><InfoCard>
<InfoRow label="Structure" value={v2.layout?.structure}/>
<InfoRow label="Hierarchy" value={v2.layout?.hierarchy}/>
<InfoRow label="Alignment" value={v2.layout?.alignment}/>
{v2.layout?.zones?.length>0&&(<div className="pt-1"><span className="text-xs text-neutral-500 dark:text-neutral-400">Zones:</span><p className="text-sm text-neutral-900 dark:text-neutral-100 mt-0.5">{v2.layout.zones.join(' • ')}</p></div>)}
</InfoCard></Section>
{/*Visual Scene*/}
{v2.visual_scene?.scene_description&&(<Section title="Scene"><InfoCard><p className="text-sm text-neutral-900 dark:text-neutral-100">{v2.visual_scene.scene_description}</p>
{v2.visual_scene?.product_placement&&(<InfoRow label="Product Placement" value={v2.visual_scene.product_placement}/>)}
{v2.visual_scene?.lifestyle_elements?.length>0&&(<div className="pt-1"><span className="text-xs text-neutral-500 dark:text-neutral-400">Lifestyle Elements:</span><p className="text-sm text-neutral-900 dark:text-neutral-100 mt-0.5">{v2.visual_scene.lifestyle_elements.join(' • ')}</p></div>)}
{v2.visual_scene?.visual_treatments?.length>0&&(<div className="pt-1"><span className="text-xs text-neutral-500 dark:text-neutral-400">Visual Treatments:</span><p className="text-sm text-neutral-900 dark:text-neutral-100 mt-0.5">{v2.visual_scene.visual_treatments.join(' • ')}</p></div>)}
</InfoCard></Section>)}
{/*Copywriting*/}
{(v2.copywriting?.headline||v2.copywriting?.benefits?.length>0)&&(<Section title="Copywriting"><InfoCard>
{v2.copywriting?.headline&&(<InfoRow label="Headline" value={v2.copywriting.headline}/>)}
{v2.copywriting?.subheadline&&(<InfoRow label="Subheadline" value={v2.copywriting.subheadline}/>)}
{v2.copywriting?.cta&&(<InfoRow label="CTA" value={v2.copywriting.cta}/>)}
{v2.copywriting?.tagline&&(<InfoRow label="Tagline" value={v2.copywriting.tagline}/>)}
{v2.copywriting?.benefits?.length>0&&(<div className="pt-1"><span className="text-xs text-neutral-500 dark:text-neutral-400">Benefits ({v2.copywriting.benefits.length}):</span><ul className="mt-1 space-y-0.5">{v2.copywriting.benefits.map((b,i)=><li key={i} className="text-sm text-neutral-900 dark:text-neutral-100">• {b}</li>)}</ul></div>)}
</InfoCard></Section>)}
{/*Constraints*/}
{(v2.constraints?.non_negotiables?.length>0||v2.constraints?.creative_freedom?.length>0)&&(<Section title="Constraints"><div className="space-y-3">
{v2.constraints?.non_negotiables?.length>0&&(<div><span className="text-xs font-medium text-brand-600 dark:text-brand-500">Must Preserve</span><ul className="mt-1 space-y-1">{v2.constraints.non_negotiables.map((item,i)=>(<li key={i} className="text-xs flex items-start gap-1.5 text-neutral-900 dark:text-neutral-100"><Check className="h-3 w-3 text-brand-500 mt-0.5 shrink-0"/>{item}</li>))}</ul></div>)}
{v2.constraints?.creative_freedom?.length>0&&(<div><span className="text-xs font-medium text-neutral-500">Can Vary</span><ul className="mt-1 space-y-1">{v2.constraints.creative_freedom.map((item,i)=>(<li key={i} className="text-xs flex items-start gap-1.5 text-neutral-500 dark:text-neutral-400"><Circle className="h-3 w-3 mt-0.5 shrink-0"/>{item}</li>))}</ul></div>)}
{v2.constraints?.product_integration&&(<div className="pt-2"><span className="text-xs text-neutral-500 dark:text-neutral-400">Product Integration:</span><p className="text-sm text-neutral-900 dark:text-neutral-100 mt-0.5">{v2.constraints.product_integration}</p></div>)}
</div></Section>)}
</>):analysis?(
//V1 Fallback display
<Section title="Analysis (V1)"><InfoCard>
<InfoRow label="Version" value="1.0 (Legacy)"/>
<InfoRow label="Aspect Ratio" value={analysis.canvas?.aspect_ratio}/>
<InfoRow label="Background" value={analysis.canvas?.background}/>
{analysis.style&&(<><InfoRow label="Mood" value={analysis.style.mood}/><InfoRow label="Lighting" value={analysis.style.lighting}/></>)}
{'elements' in analysis&&(<InfoRow label="Elements" value={`${(analysis as any).elements?.length||0} defined`}/>)}
{'product_slot' in analysis&&(<InfoRow label="Product Slot" value={(analysis as any).product_slot?'Yes':'No'}/>)}
</InfoCard></Section>):(<div className="text-sm text-neutral-500 dark:text-neutral-400 py-4">No analysis data available. Click Edit to add reference images.</div>)}
</div>
</div>
)}</DialogContent></Dialog>)}
