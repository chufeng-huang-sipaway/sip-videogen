import { useState, useEffect, useRef } from 'react'
import { Package, X, Pencil } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuTrigger,
} from '@/components/ui/context-menu'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useProducts } from '@/context/ProductContext'
import { useBrand } from '@/context/BrandContext'
import { bridge, isPyWebView, type ProductEntry } from '@/lib/bridge'
import { EditProductDialog } from '../EditProductDialog'

//Thumbnail component for product images (small size only)
function Thumb({path}:{path:string}){
const[src,setSrc]=useState<string|null>(null)
useEffect(()=>{let c=false
async function load(){if(!isPyWebView()||!path)return;try{const u=await bridge.getProductImageThumbnail(path);if(!c)setSrc(u)}catch{}}
load();return()=>{c=true}},[path])
if(!src)return<div className="h-8 w-8 rounded bg-muted flex items-center justify-center shrink-0"><Package className="h-4 w-4 text-muted-foreground"/></div>
return<img src={src} alt="" className="h-8 w-8 rounded object-cover shrink-0 transition-opacity duration-200"/>}

interface ProductCardProps {product:ProductEntry;isAttached:boolean;onOpenModal:()=>void;onAttach:()=>void;onDetach:()=>void;onEdit:()=>void;onDelete:()=>void}
function ProductCard({product,isAttached,onOpenModal,onAttach,onDetach,onEdit,onDelete}:ProductCardProps){
const didDragRef=useRef(false)
const pointerStartRef=useRef<{x:number;y:number}|null>(null)
const handlePointerDown=(e:React.PointerEvent)=>{pointerStartRef.current={x:e.clientX,y:e.clientY};didDragRef.current=false}
const handlePointerMove=(e:React.PointerEvent)=>{if(!pointerStartRef.current)return;const dx=Math.abs(e.clientX-pointerStartRef.current.x);const dy=Math.abs(e.clientY-pointerStartRef.current.y);if(dx>5||dy>5)didDragRef.current=true}
const handlePointerUp=()=>{pointerStartRef.current=null}
const handlePointerCancel=()=>{pointerStartRef.current=null;didDragRef.current=false}
const handleDragStart=(e:React.DragEvent)=>{didDragRef.current=true;e.dataTransfer.setData('text/plain',product.slug);try{e.dataTransfer.setData('application/x-brand-product',product.slug)}catch{};e.dataTransfer.effectAllowed='copy'}
const handleDragEnd=()=>{setTimeout(()=>{didDragRef.current=false},0)}
const handleClick=()=>{if(didDragRef.current){didDragRef.current=false;return};onOpenModal()}
const handleKeyDown=(e:React.KeyboardEvent)=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();onOpenModal()}}
return(<div><ContextMenu><ContextMenuTrigger asChild><div role="button" tabIndex={0} className={`flex items-center gap-2.5 py-2 px-2.5 rounded-lg cursor-pointer group overflow-hidden transition-all duration-150 hover:translate-x-0.5 ${isAttached?'bg-primary/10 text-foreground shadow-[inset_2px_0_0_0_var(--color-primary)]':'text-muted-foreground/80 hover:bg-muted/50 hover:text-foreground'}`} draggable onDragStart={handleDragStart} onDragEnd={handleDragEnd} onPointerDown={handlePointerDown} onPointerMove={handlePointerMove} onPointerUp={handlePointerUp} onPointerCancel={handlePointerCancel} onClick={handleClick} onKeyDown={handleKeyDown} title="Click to preview, drag to attach to chat"><Thumb path={product.primary_image}/><div className="flex-1 min-w-0 overflow-hidden"><div className="flex items-center gap-1.5"><span className={`text-sm truncate ${isAttached?'font-medium text-foreground':'text-foreground/90'}`}>{product.name}</span></div><span className="text-xs text-muted-foreground/70 truncate block">{product.description.length>50?product.description.slice(0,50)+'...':product.description}</span></div></div></ContextMenuTrigger>
<ContextMenuContent>{isAttached?(<ContextMenuItem onClick={onDetach}>Detach from Chat</ContextMenuItem>):(<ContextMenuItem onClick={onAttach}>Attach to Chat</ContextMenuItem>)}<ContextMenuSeparator/><ContextMenuItem onClick={onEdit}><Pencil className="h-4 w-4 mr-2"/>Edit Product</ContextMenuItem><ContextMenuSeparator/><ContextMenuItem onClick={onDelete} className="text-destructive">Delete Product</ContextMenuItem></ContextMenuContent></ContextMenu></div>)}

export function ProductsSection() {
  const { activeBrand } = useBrand()
  const {
    products,
    attachedProducts,
    isLoading,
    error,
    refresh,
    attachProduct,
    detachProduct,
    deleteProduct,
  } = useProducts()
  const [actionError,setActionError]=useState<string|null>(null)
  const [editingProductSlug,setEditingProductSlug]=useState<string|null>(null)
  useEffect(()=>{if(actionError){const t=setTimeout(()=>setActionError(null),5000);return()=>clearTimeout(t)}},[actionError])
  const handleDelete=async(slug:string)=>{if(confirm(`Delete product "${slug}"? This cannot be undone.`)){try{await deleteProduct(slug)}catch(err){setActionError(err instanceof Error?err.message:'Failed to delete product')}}}

  if (!activeBrand) {
    return <div className="text-sm text-muted-foreground">Select a brand</div>
  }

  if (error) {
    return (
      <div className="text-sm text-destructive">
        Error: {error}
        <Button variant="ghost" size="sm" onClick={refresh}>
          Retry
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-1 pl-1 pr-1">{actionError&&(<Alert variant="destructive" className="py-2 px-3 mb-2"><AlertDescription className="flex items-center justify-between text-xs"><span>{actionError}</span><Button variant="ghost" size="icon" className="h-4 w-4 shrink-0" onClick={()=>setActionError(null)}><X className="h-3 w-3"/></Button></AlertDescription></Alert>)}{products.length===0?(<p className="text-xs text-muted-foreground py-2 px-2">{isLoading?'Loading...':'No products yet. Click + to add one.'}</p>):(<div className="space-y-0.5">{products.map((product)=>(<ProductCard key={product.slug} product={product} isAttached={attachedProducts.includes(product.slug)} onOpenModal={()=>setEditingProductSlug(product.slug)} onAttach={()=>attachProduct(product.slug)} onDetach={()=>detachProduct(product.slug)} onEdit={()=>setEditingProductSlug(product.slug)} onDelete={()=>handleDelete(product.slug)}/>))}</div>)}
{editingProductSlug&&(<EditProductDialog open={!!editingProductSlug} onOpenChange={(o)=>{if(!o)setEditingProductSlug(null)}} productSlug={editingProductSlug}/>)}</div>)}
