import{useState,useEffect}from'react'
import{Layout,Star,Pencil,Trash2,Link,Unlink,Lock,Unlock,Loader2}from'lucide-react'
import{Dialog,DialogContent,DialogHeader,DialogTitle,DialogDescription,DialogFooter}from'@/components/ui/dialog'
import{Button}from'@/components/ui/button'
import{useTemplates}from'@/context/TemplateContext'
import{bridge,isPyWebView,type TemplateFull}from'@/lib/bridge'
interface TemplateModalProps{slug:string|null;onClose:()=>void;onEdit:(slug:string)=>void;onDelete:(slug:string)=>void}
function Thumb({path,alt}:{path:string;alt:string}){
const[src,setSrc]=useState<string|null>(null)
useEffect(()=>{let c=false
async function load(){if(!isPyWebView()||!path)return
try{const u=await bridge.getTemplateImageFull(path);if(!c)setSrc(u)}catch{}}
load();return()=>{c=true}},[path])
if(!src)return<div className="h-24 w-24 rounded bg-muted flex items-center justify-center shrink-0"><Loader2 className="h-4 w-4 text-muted-foreground animate-spin"/></div>
return<img src={src} alt={alt} className="h-24 w-24 rounded object-cover shrink-0"/>}
export function TemplateModal({slug,onClose,onEdit,onDelete}:TemplateModalProps){
const{getTemplate,getTemplateImages,attachTemplate,detachTemplate,setTemplateStrictness,attachedTemplates}=useTemplates()
const[template,setTemplate]=useState<TemplateFull|null>(null)
const[images,setImages]=useState<string[]>([])
const[isLoading,setIsLoading]=useState(false)
const[error,setError]=useState<string|null>(null)
const[isMutating,setIsMutating]=useState(false)
const attached=slug?attachedTemplates.find(t=>t.template_slug===slug):null
const isAttached=!!attached
const isStrict=attached?.strict??template?.default_strict??true
//Fetch template data on slug change
useEffect(()=>{setTemplate(null);setImages([]);setError(null)
if(!slug)return
let c=false;setIsLoading(true)
Promise.all([getTemplate(slug),getTemplateImages(slug)])
.then(([t,i])=>{if(!c){setTemplate(t);setImages(i)}})
.catch(e=>{if(!c)setError(e.message||'Failed to load template')})
.finally(()=>{if(!c)setIsLoading(false)})
return()=>{c=true}},[slug,getTemplate,getTemplateImages])
const handleAttachToggle=async()=>{if(!slug)return;setIsMutating(true)
try{isAttached?detachTemplate(slug):attachTemplate(slug)}finally{setIsMutating(false)}}
const handleStrictToggle=async()=>{if(!slug||!isAttached)return;setIsMutating(true)
try{setTemplateStrictness(slug,!isStrict)}finally{setIsMutating(false)}}
const handleEdit=()=>{if(slug)onEdit(slug)}
const handleDelete=()=>{if(slug)onDelete(slug)}
return(<Dialog open={!!slug} onOpenChange={o=>{if(!o)onClose()}}>
<DialogContent className="max-h-[80vh] overflow-y-auto max-w-lg">
<DialogHeader><DialogTitle className="flex items-center gap-2"><Layout className="h-5 w-5 text-brand-500"/>{isLoading?'Loading...':template?.name||'Template'}</DialogTitle>
<DialogDescription>{template?.description||''}</DialogDescription></DialogHeader>
{isLoading&&(<div className="py-8 flex items-center justify-center gap-2 text-sm text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin"/>Loading template...</div>)}
{error&&!isLoading&&(<div className="py-8 text-center text-sm text-destructive">{error}</div>)}
{!isLoading&&!error&&!template&&(<div className="py-8 text-center text-sm text-muted-foreground">Template not found</div>)}
{!isLoading&&!error&&template&&(<div className="space-y-4">
{/* Image Gallery */}
{images.length>0&&(<div className="flex flex-wrap gap-2">{images.map((path)=>(<div key={path} className={`relative rounded-md overflow-hidden ${path===template.primary_image?'ring-2 ring-primary ring-offset-2':'ring-1 ring-border/50'}`}><Thumb path={path} alt={template.name}/>{path===template.primary_image&&(<div className="absolute top-1 left-1 bg-primary text-primary-foreground rounded-full p-0.5 shadow-sm"><Star className="h-2.5 w-2.5 fill-current"/></div>)}</div>))}</div>)}
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
<Button variant="outline" size="sm" onClick={handleAttachToggle} disabled={isMutating||!template}>
{isMutating?<Loader2 className="h-4 w-4 animate-spin mr-1"/>:isAttached?<Unlink className="h-4 w-4 mr-1"/>:<Link className="h-4 w-4 mr-1"/>}
{isAttached?'Detach':'Attach'}</Button>
{isAttached&&(<Button variant="outline" size="sm" onClick={handleStrictToggle} disabled={isMutating}>
{isMutating?<Loader2 className="h-4 w-4 animate-spin mr-1"/>:isStrict?<Unlock className="h-4 w-4 mr-1"/>:<Lock className="h-4 w-4 mr-1"/>}
{isStrict?'Make Loose':'Make Strict'}</Button>)}
<div className="flex-1"/>
<Button variant="outline" size="sm" onClick={handleEdit} disabled={!template}><Pencil className="h-4 w-4 mr-1"/>Edit</Button>
<Button variant="destructive" size="sm" onClick={handleDelete} disabled={!template}><Trash2 className="h-4 w-4 mr-1"/>Delete</Button>
</DialogFooter></DialogContent></Dialog>)}
