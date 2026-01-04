import{useState,useEffect}from'react'
import{Layout,Star,Pencil,Trash2,Link,Unlink,Lock,Unlock,Loader2}from'lucide-react'
import{Dialog,DialogContent,DialogHeader,DialogTitle,DialogDescription,DialogFooter}from'@/components/ui/dialog'
import{Button}from'@/components/ui/button'
import{useStyleReferences}from'@/context/StyleReferenceContext'
import{bridge,isPyWebView,type StyleReferenceFull}from'@/lib/bridge'
interface StyleReferenceModalProps{slug:string|null;onClose:()=>void;onEdit:(slug:string)=>void;onDelete:(slug:string)=>void}
function Thumb({path,alt}:{path:string;alt:string}){
const[src,setSrc]=useState<string|null>(null)
useEffect(()=>{let c=false
async function load(){if(!isPyWebView()||!path)return
try{const u=await bridge.getStyleReferenceImageFull(path);if(!c)setSrc(u)}catch{}}
load();return()=>{c=true}},[path])
if(!src)return<div className="h-24 w-24 rounded bg-muted flex items-center justify-center shrink-0"><Loader2 className="h-4 w-4 text-muted-foreground animate-spin"/></div>
return<img src={src} alt={alt} className="h-24 w-24 rounded object-cover shrink-0"/>}
export function StyleReferenceModal({slug,onClose,onEdit,onDelete}:StyleReferenceModalProps){
const{getStyleReference,getStyleReferenceImages,attachStyleReference,detachStyleReference,setStyleReferenceStrictness,attachedStyleReferences}=useStyleReferences()
const[styleRef,setStyleRef]=useState<StyleReferenceFull|null>(null)
const[images,setImages]=useState<string[]>([])
const[isLoading,setIsLoading]=useState(false)
const[error,setError]=useState<string|null>(null)
const[isMutating,setIsMutating]=useState(false)
const attached=slug?attachedStyleReferences.find(t=>t.style_reference_slug===slug):null
const isAttached=!!attached
const isStrict=attached?.strict??styleRef?.default_strict??true
//Fetch style reference data on slug change
useEffect(()=>{setStyleRef(null);setImages([]);setError(null)
if(!slug)return
let c=false;setIsLoading(true)
Promise.all([getStyleReference(slug),getStyleReferenceImages(slug)])
.then(([t,i])=>{if(!c){setStyleRef(t);setImages(i)}})
.catch(e=>{if(!c)setError(e.message||'Failed to load style reference')})
.finally(()=>{if(!c)setIsLoading(false)})
return()=>{c=true}},[slug,getStyleReference,getStyleReferenceImages])
const handleAttachToggle=async()=>{if(!slug)return;setIsMutating(true)
try{isAttached?detachStyleReference(slug):attachStyleReference(slug)}finally{setIsMutating(false)}}
const handleStrictToggle=async()=>{if(!slug||!isAttached)return;setIsMutating(true)
try{setStyleReferenceStrictness(slug,!isStrict)}finally{setIsMutating(false)}}
const handleEdit=()=>{if(slug)onEdit(slug)}
const handleDelete=()=>{if(slug)onDelete(slug)}
return(<Dialog open={!!slug} onOpenChange={o=>{if(!o)onClose()}}>
<DialogContent className="max-h-[80vh] overflow-y-auto max-w-lg">
<DialogHeader><DialogTitle className="flex items-center gap-2"><Layout className="h-5 w-5 text-brand-500"/>{isLoading?'Loading...':styleRef?.name||'Style Reference'}</DialogTitle>
<DialogDescription>{styleRef?.description||''}</DialogDescription></DialogHeader>
{isLoading&&(<div className="py-8 flex items-center justify-center gap-2 text-sm text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin"/>Loading style reference...</div>)}
{error&&!isLoading&&(<div className="py-8 text-center text-sm text-destructive">{error}</div>)}
{!isLoading&&!error&&!styleRef&&(<div className="py-8 text-center text-sm text-muted-foreground">Style reference not found</div>)}
{!isLoading&&!error&&styleRef&&(<div className="space-y-4">
{/* Image Gallery */}
{images.length>0&&(<div className="flex flex-wrap gap-2">{images.map((path)=>(<div key={path} className={`relative rounded-md overflow-hidden ${path===styleRef.primary_image?'ring-2 ring-primary ring-offset-2':'ring-1 ring-border/50'}`}><Thumb path={path} alt={styleRef.name}/>{path===styleRef.primary_image&&(<div className="absolute top-1 left-1 bg-primary text-primary-foreground rounded-full p-0.5 shadow-sm"><Star className="h-2.5 w-2.5 fill-current"/></div>)}</div>))}</div>)}
{images.length===0&&(<div className="py-4 text-center text-xs text-muted-foreground">No images</div>)}
{/* Strictness Indicator */}
<div className="flex items-center gap-2 text-sm">
{isStrict?<Lock className="h-4 w-4 text-amber-500"/>:<Unlock className="h-4 w-4 text-muted-foreground"/>}
<span className={isStrict?'text-amber-600 dark:text-amber-400':'text-muted-foreground'}>{isStrict?'Strict mode':'Loose mode'}</span>
</div>
{/* Metadata */}
<div className="flex items-center gap-3 text-xs text-muted-foreground pt-2 border-t border-border">
<span>{images.length} image{images.length!==1?'s':''}</span>
</div></div>)}
<DialogFooter className="flex-col sm:flex-row gap-2 pt-4">
<Button variant="outline" size="sm" onClick={handleAttachToggle} disabled={isMutating||!styleRef}>
{isMutating?<Loader2 className="h-4 w-4 animate-spin mr-1"/>:isAttached?<Unlink className="h-4 w-4 mr-1"/>:<Link className="h-4 w-4 mr-1"/>}
{isAttached?'Detach':'Attach'}</Button>
{isAttached&&(<Button variant="outline" size="sm" onClick={handleStrictToggle} disabled={isMutating}>
{isMutating?<Loader2 className="h-4 w-4 animate-spin mr-1"/>:isStrict?<Unlock className="h-4 w-4 mr-1"/>:<Lock className="h-4 w-4 mr-1"/>}
{isStrict?'Make Loose':'Make Strict'}</Button>)}
<div className="flex-1"/>
<Button variant="outline" size="sm" onClick={handleEdit} disabled={!styleRef}><Pencil className="h-4 w-4 mr-1"/>Edit</Button>
<Button variant="destructive" size="sm" onClick={handleDelete} disabled={!styleRef}><Trash2 className="h-4 w-4 mr-1"/>Delete</Button>
</DialogFooter></DialogContent></Dialog>)}
