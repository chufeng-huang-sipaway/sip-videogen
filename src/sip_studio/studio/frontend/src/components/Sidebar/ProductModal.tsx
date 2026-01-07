import{useState,useEffect}from'react'
import{Package,Star,Pencil,Trash2,Link,Unlink,Loader2}from'lucide-react'
import{Dialog,DialogContent,DialogHeader,DialogTitle,DialogDescription,DialogFooter}from'@/components/ui/dialog'
import{Button}from'@/components/ui/button'
import{useProducts}from'@/context/ProductContext'
import{bridge,isPyWebView,type ProductFull}from'@/lib/bridge'
interface ProductModalProps{slug:string|null;onClose:()=>void;onEdit:(slug:string)=>void;onDelete:(slug:string)=>void}
function Thumb({path,alt}:{path:string;alt:string}){
const[src,setSrc]=useState<string|null>(null)
useEffect(()=>{let c=false
async function load(){if(!isPyWebView()||!path)return
try{const u=await bridge.getProductImageFull(path);if(!c)setSrc(u)}catch{}}
load();return()=>{c=true}},[path])
if(!src)return<div className="h-24 w-24 rounded bg-muted flex items-center justify-center shrink-0"><Loader2 className="h-4 w-4 text-muted-foreground animate-spin"/></div>
return<img src={src} alt={alt} className="h-24 w-24 rounded object-cover shrink-0"/>}
export function ProductModal({slug,onClose,onEdit,onDelete}:ProductModalProps){
const{getProduct,getProductImages,attachProduct,detachProduct,attachedProducts}=useProducts()
const[product,setProduct]=useState<ProductFull|null>(null)
const[images,setImages]=useState<string[]>([])
const[isLoading,setIsLoading]=useState(false)
const[error,setError]=useState<string|null>(null)
const[isMutating,setIsMutating]=useState(false)
const isAttached=slug?attachedProducts.includes(slug):false
//Fetch product data on slug change
useEffect(()=>{setProduct(null);setImages([]);setError(null)
if(!slug)return
let c=false;setIsLoading(true)
Promise.all([getProduct(slug),getProductImages(slug)])
.then(([p,i])=>{if(!c){setProduct(p);setImages(i)}})
.catch(e=>{if(!c)setError(e.message||'Failed to load product')})
.finally(()=>{if(!c)setIsLoading(false)})
return()=>{c=true}},[slug,getProduct,getProductImages])
const handleAttachToggle=async()=>{if(!slug)return;setIsMutating(true)
try{isAttached?detachProduct(slug):attachProduct(slug)}finally{setIsMutating(false)}}
const handleEdit=()=>{if(slug)onEdit(slug)}
const handleDelete=()=>{if(slug)onDelete(slug)}
return(<Dialog open={!!slug} onOpenChange={o=>{if(!o)onClose()}}>
<DialogContent className="max-h-[80vh] overflow-y-auto max-w-lg">
<DialogHeader><DialogTitle className="flex items-center gap-2"><Package className="h-5 w-5 text-brand-500"/>{isLoading?'Loading...':product?.name||'Product'}</DialogTitle>
<DialogDescription>{product?.description||''}</DialogDescription></DialogHeader>
{isLoading&&(<div className="py-8 flex items-center justify-center gap-2 text-sm text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin"/>Loading product...</div>)}
{error&&!isLoading&&(<div className="py-8 text-center text-sm text-destructive">{error}</div>)}
{!isLoading&&!error&&!product&&(<div className="py-8 text-center text-sm text-muted-foreground">Product not found</div>)}
{!isLoading&&!error&&product&&(<div className="space-y-4">
{/* Image Gallery */}
{images.length>0&&(<div className="flex flex-wrap gap-2">{images.map((path)=>(<div key={path} className={`relative rounded-md overflow-hidden ${path===product.primary_image?'ring-2 ring-primary ring-offset-2':'ring-1 ring-border/50'}`}><Thumb path={path} alt={product.name}/>{path===product.primary_image&&(<div className="absolute top-1 left-1 bg-primary text-primary-foreground rounded-full p-0.5 shadow-sm"><Star className="h-2.5 w-2.5 fill-current"/></div>)}</div>))}</div>)}
{images.length===0&&(<div className="py-4 text-center text-xs text-muted-foreground">No images</div>)}
{/* Metadata */}
<div className="flex items-center gap-3 text-xs text-muted-foreground pt-2 border-t border-border">
<span>{images.length} image{images.length!==1?'s':''}</span>
{product.attributes.length>0&&<span>{product.attributes.length} attribute{product.attributes.length!==1?'s':''}</span>}
</div></div>)}
<DialogFooter className="flex-col sm:flex-row gap-2 pt-4">
<Button variant="outline" size="sm" onClick={handleAttachToggle} disabled={isMutating||!product}>
{isMutating?<Loader2 className="h-4 w-4 animate-spin mr-1"/>:isAttached?<Unlink className="h-4 w-4 mr-1"/>:<Link className="h-4 w-4 mr-1"/>}
{isAttached?'Detach':'Attach'}</Button>
<div className="flex-1"/>
<Button variant="outline" size="sm" onClick={handleEdit} disabled={!product}><Pencil className="h-4 w-4 mr-1"/>Edit</Button>
<Button variant="destructive" size="sm" onClick={handleDelete} disabled={!product}><Trash2 className="h-4 w-4 mr-1"/>Delete</Button>
</DialogFooter></DialogContent></Dialog>)}
