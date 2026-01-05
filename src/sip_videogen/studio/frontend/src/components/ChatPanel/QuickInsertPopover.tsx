import {useState,useEffect,useMemo,useRef,useCallback} from 'react'
import {Search,Package,FileImage,Check,Upload} from 'lucide-react'
import * as Popover from '@radix-ui/react-popover'
import {Tabs,TabsList,TabsTrigger,TabsContent} from '@/components/ui/tabs'
import {useProducts} from '@/context/ProductContext'
import {useStyleReferences} from '@/context/StyleReferenceContext'
import {bridge,isPyWebView,type ProductEntry,type StyleReferenceSummary} from '@/lib/bridge'
//Thumbnail component for products
function ProdThumb({path}:{path:string}){
const [src,setSrc]=useState<string|null>(null)
useEffect(()=>{
let c=false
async function ld(){
if(!isPyWebView()||!path)return
try{const u=await bridge.getProductImageThumbnail(path);if(!c)setSrc(u)}catch{}}
ld()
return()=>{c=true}},[path])
if(!src)return(<div className="h-9 w-9 rounded-lg bg-muted flex items-center justify-center shrink-0"><Package className="h-4 w-4 text-muted-foreground/50"/></div>)
return <img src={src} alt="" className="h-9 w-9 rounded-lg object-cover shrink-0 ring-1 ring-border/20"/>}
//Thumbnail component for style references
function SrThumb({path}:{path:string}){
const [src,setSrc]=useState<string|null>(null)
useEffect(()=>{
let c=false
async function ld(){
if(!isPyWebView()||!path)return
try{const u=await bridge.getStyleReferenceImageThumbnail(path);if(!c)setSrc(u)}catch{}}
ld()
return()=>{c=true}},[path])
if(!src)return(<div className="h-9 w-9 rounded-lg bg-muted flex items-center justify-center shrink-0"><FileImage className="h-4 w-4 text-muted-foreground/50"/></div>)
return <img src={src} alt="" className="h-9 w-9 rounded-lg object-cover shrink-0 ring-1 ring-border/20"/>}
interface QuickInsertPopoverProps {
open:boolean
onOpenChange:(open:boolean)=>void
trigger:React.ReactNode
onUploadImage?:()=>void}
export function QuickInsertPopover({open,onOpenChange,trigger,onUploadImage}:QuickInsertPopoverProps){
const {products,attachedProducts,attachProduct,detachProduct}=useProducts()
const {styleReferences,attachedStyleReferences,attachStyleReference,detachStyleReference}=useStyleReferences()
const [tab,setTab]=useState<'products'|'styles'>('products')
const [query,setQuery]=useState('')
const searchRef=useRef<HTMLInputElement>(null)
const listRef=useRef<HTMLDivElement>(null)
const [hlIdx,setHlIdx]=useState(0)
//Reset on open/close
useEffect(()=>{if(open){setQuery('');setHlIdx(0);setTimeout(()=>searchRef.current?.focus(),50)}else{setQuery('')}},[open])
//Filter products
const filteredProds=useMemo(()=>{
if(!query.trim())return products
const q=query.toLowerCase()
return products.filter(p=>p.name.toLowerCase().includes(q)||p.description?.toLowerCase().includes(q))},[products,query])
//Filter style references
const filteredSrs=useMemo(()=>{
if(!query.trim())return styleReferences
const q=query.toLowerCase()
return styleReferences.filter(sr=>sr.name.toLowerCase().includes(q)||sr.description?.toLowerCase().includes(q))},[styleReferences,query])
const curList=tab==='products'?filteredProds:filteredSrs
const maxIdx=curList.length-1
//Reset highlight when list/tab changes
useEffect(()=>{setHlIdx(0)},[tab,query])
//Scroll highlighted item into view
useEffect(()=>{
if(!listRef.current)return
const el=listRef.current.querySelector(`[data-idx="${hlIdx}"]`)
el?.scrollIntoView({block:'nearest'})},[hlIdx])
const toggleProd=useCallback((slug:string)=>{
if(attachedProducts.includes(slug))detachProduct(slug)
else attachProduct(slug)},[attachedProducts,attachProduct,detachProduct])
const toggleSr=useCallback((slug:string)=>{
const att=attachedStyleReferences.some(sr=>sr.style_reference_slug===slug)
if(att)detachStyleReference(slug)
else attachStyleReference(slug)},[attachedStyleReferences,attachStyleReference,detachStyleReference])
const handleKeyDown=(e:React.KeyboardEvent)=>{
if(e.key==='ArrowDown'){e.preventDefault();setHlIdx(i=>Math.min(i+1,maxIdx))}
else if(e.key==='ArrowUp'){e.preventDefault();setHlIdx(i=>Math.max(i-1,0))}
else if(e.key==='Enter'&&curList.length>0){
e.preventDefault()
if(tab==='products')toggleProd((curList[hlIdx] as ProductEntry).slug)
else toggleSr((curList[hlIdx] as StyleReferenceSummary).slug)}
else if(e.key==='Escape'){onOpenChange(false)}}
return(
<Popover.Root open={open} onOpenChange={onOpenChange}>
<Popover.Trigger asChild>{trigger}</Popover.Trigger>
<Popover.Portal>
<Popover.Content align="start" sideOffset={10} className="z-50 w-72 rounded-2xl border border-border/30 bg-popover text-popover-foreground shadow-float p-3 animate-in fade-in-0 zoom-in-95 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95" onKeyDown={handleKeyDown}>
<Tabs value={tab} onValueChange={v=>setTab(v as 'products'|'styles')} className="w-full">
<TabsList className="w-full grid grid-cols-2 mb-2">
<TabsTrigger value="products" className="text-xs">Products</TabsTrigger>
<TabsTrigger value="styles" className="text-xs">Styles</TabsTrigger>
</TabsList>
{/* Search input */}
<div className="relative mb-2">
<Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/70"/>
<input ref={searchRef} type="text" placeholder={`Search ${tab}...`} value={query} onChange={e=>setQuery(e.target.value)} className="w-full h-8 pl-8 pr-3 rounded-lg bg-transparent text-xs text-foreground placeholder:text-muted-foreground/70 focus:outline-none focus:bg-muted/30"/>
</div>
{/* Products list */}
<TabsContent value="products" className="mt-0">
<div ref={tab==='products'?listRef:undefined} className="max-h-48 overflow-y-auto -mx-1">
{filteredProds.length===0?(<div className="py-6 text-center text-muted-foreground text-xs">{query?'No products match':'No products'}</div>):(
<div className="space-y-0.5 px-1">{filteredProds.map((p,i)=>{
const att=attachedProducts.includes(p.slug)
return(<button key={p.slug} data-idx={i} onClick={()=>toggleProd(p.slug)} className={`w-full flex items-center gap-2.5 p-1.5 rounded-lg text-left transition-colors ${att?'bg-primary/10 hover:bg-primary/15':hlIdx===i?'bg-muted':'hover:bg-muted'}`}>
<ProdThumb path={p.primary_image}/>
<div className="flex-1 min-w-0"><div className="font-medium text-xs text-foreground truncate">{p.name}</div>{p.description&&<div className="text-[10px] text-muted-foreground truncate">{p.description}</div>}</div>
{att&&<Check className="h-3.5 w-3.5 text-primary shrink-0"/>}
</button>)})}</div>)}</div>
</TabsContent>
{/* Style references list */}
<TabsContent value="styles" className="mt-0">
<div ref={tab==='styles'?listRef:undefined} className="max-h-48 overflow-y-auto -mx-1">
{filteredSrs.length===0?(<div className="py-6 text-center text-muted-foreground text-xs">{query?'No styles match':'No style references'}</div>):(
<div className="space-y-0.5 px-1">{filteredSrs.map((sr,i)=>{
const att=attachedStyleReferences.some(a=>a.style_reference_slug===sr.slug)
return(<button key={sr.slug} data-idx={i} onClick={()=>toggleSr(sr.slug)} className={`w-full flex items-center gap-2.5 p-1.5 rounded-lg text-left transition-colors ${att?'bg-primary/10 hover:bg-primary/15':hlIdx===i?'bg-muted':'hover:bg-muted'}`}>
<SrThumb path={sr.primary_image}/>
<div className="flex-1 min-w-0"><div className="font-medium text-xs text-foreground truncate">{sr.name}</div>{sr.description&&<div className="text-[10px] text-muted-foreground truncate">{sr.description}</div>}</div>
{att&&<Check className="h-3.5 w-3.5 text-primary shrink-0"/>}
</button>)})}</div>)}</div>
</TabsContent>
</Tabs>
{/* Upload Image action */}
{onUploadImage&&(<button onClick={()=>{onUploadImage();onOpenChange(false)}} className="w-full flex items-center gap-2 px-2 py-2 mt-2 pt-3 border-t border-border/20 text-xs text-muted-foreground hover:text-foreground hover:bg-muted/50 rounded-lg transition-colors">
<Upload className="h-3.5 w-3.5"/><span>Upload Image</span></button>)}
</Popover.Content>
</Popover.Portal>
</Popover.Root>)}
