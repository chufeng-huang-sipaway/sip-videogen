import{useState,useEffect,useRef}from'react'
import{Package,X}from'lucide-react'
import{Button}from'@/components/ui/button'
import{Alert,AlertDescription}from'@/components/ui/alert'
import{useProducts}from'@/context/ProductContext'
import{useBrand}from'@/context/BrandContext'
import{useTabs}from'@/context/TabContext'
import{bridge,isPyWebView,type ProductEntry}from'@/lib/bridge'
import{makeTabId}from'@/types/tabs'
//Thumbnail component for product images
function ProductThumbnail({path}:{path:string}){
const[src,setSrc]=useState<string|null>(null)
useEffect(()=>{let cancelled=false
async function load(){if(!isPyWebView()||!path)return
try{const dataUrl=await bridge.getProductImageThumbnail(path);if(!cancelled)setSrc(dataUrl)}catch{/*ignore*/}}
load();return()=>{cancelled=true}},[path])
if(!src)return(<div className="h-8 w-8 rounded bg-muted flex items-center justify-center shrink-0"><Package className="h-4 w-4 text-muted-foreground"/></div>)
return<img src={src} alt="" className="h-8 w-8 rounded object-cover shrink-0"/>}
//Product row component with drag support
interface ProductRowProps{product:ProductEntry;isTabOpen:boolean;onClick:()=>void}
function ProductRow({product,isTabOpen,onClick}:ProductRowProps){
const mouseDownPos=useRef<{x:number;y:number}|null>(null)
const isDragging=useRef(false)
const handleDragStart=(e:React.DragEvent)=>{isDragging.current=true
e.dataTransfer.setData('text/plain',product.slug)
try{e.dataTransfer.setData('application/x-brand-product',product.slug)}catch{/*ignore*/}
e.dataTransfer.effectAllowed='copy'}
const handleMouseDown=(e:React.MouseEvent)=>{mouseDownPos.current={x:e.clientX,y:e.clientY};isDragging.current=false}
const handleMouseUp=(e:React.MouseEvent)=>{if(!mouseDownPos.current)return
const dx=Math.abs(e.clientX-mouseDownPos.current.x)
const dy=Math.abs(e.clientY-mouseDownPos.current.y)
//Only treat as click if delta < 5px
if(dx<5&&dy<5&&!isDragging.current)onClick()
mouseDownPos.current=null}
const handleDragEnd=()=>{mouseDownPos.current=null;isDragging.current=false}
return(<div className={`flex items-center gap-2.5 py-1.5 px-2 rounded-md border border-transparent hover:bg-sidebar-accent/50 cursor-pointer group overflow-hidden transition-all duration-200 ${isTabOpen?'bg-sidebar-accent/50 border-input shadow-sm':'text-muted-foreground/80 hover:text-foreground'}`}
draggable onDragStart={handleDragStart} onDragEnd={handleDragEnd} onMouseDown={handleMouseDown} onMouseUp={handleMouseUp} title="Click to open, drag to attach to chat">
<ProductThumbnail path={product.primary_image}/>
<div className="flex-1 min-w-0 overflow-hidden">
<div className="flex items-center gap-1.5"><span className="text-sm font-medium truncate text-foreground/90">{product.name}</span></div>
<span className="text-xs text-muted-foreground truncate block">{product.description.length>40?product.description.slice(0,40)+'...':product.description}</span>
</div></div>)}
export function ProductsSection(){
const{activeBrand}=useBrand()
const{products,isLoading,error,refresh}=useProducts()
const{tabs,openTab}=useTabs()
const[actionError,setActionError]=useState<string|null>(null)
useEffect(()=>{if(actionError){const timer=setTimeout(()=>setActionError(null),5000);return()=>clearTimeout(timer)}},[actionError])
//Check if a product tab is open
const isProductTabOpen=(slug:string)=>{if(!activeBrand)return false;const tabId=makeTabId(activeBrand,'product',slug);return tabs.some(t=>t.id===tabId)}
//Handle click to open tab
const handleProductClick=(slug:string,name:string)=>{openTab('product',slug,name)}
if(!activeBrand)return<div className="text-sm text-muted-foreground">Select a brand</div>
if(error)return(<div className="text-sm text-red-500">Error: {error}<Button variant="ghost" size="sm" onClick={refresh}>Retry</Button></div>)
return(<div className="space-y-2 pl-2 pr-1">
{actionError&&(<Alert variant="destructive" className="py-2 px-3"><AlertDescription className="flex items-center justify-between text-xs"><span>{actionError}</span><Button variant="ghost" size="icon" className="h-4 w-4 shrink-0" onClick={()=>setActionError(null)}><X className="h-3 w-3"/></Button></AlertDescription></Alert>)}
{products.length===0?(<p className="text-sm text-muted-foreground italic">{isLoading?'Loading...':'No products yet. Click + to add one.'}</p>):(<div className="space-y-1">{products.map((product)=>(<ProductRow key={product.slug} product={product} isTabOpen={isProductTabOpen(product.slug)} onClick={()=>handleProductClick(product.slug,product.name)}/>))}</div>)}
</div>)}
