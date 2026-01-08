//CapsuleSelector for product/style reference selection in Playground mode
import{useState,useRef,useEffect}from'react'
import{ChevronDown,Check,Search,Package,Palette}from'lucide-react'
import{cn}from'@/lib/utils'
import{DropdownMenu,DropdownMenuTrigger,DropdownMenuContent}from'@/components/ui/dropdown-menu'
import{bridge,isPyWebView}from'@/lib/bridge'
type SelectableItem={slug:string;name:string;description?:string;imagePath?:string}
type ItemType='product'|'style'
interface Props{items:SelectableItem[];value:string;onChange:(v:string)=>void;disabled?:boolean;placeholder:string;emptyLabel:string;type:ItemType}
const thumbCache=new Map<string,string>()
//Get thumbnail using the correct bridge method based on type
async function getThumbnail(path:string,type:ItemType):Promise<string>{
if(type==='product')return bridge.getProductImageThumbnail(path)
return bridge.getStyleReferenceImageThumbnail(path)}
function ItemThumb({path,type,fallback}:{path?:string;type:ItemType;fallback:React.ReactNode}){
const[src,setSrc]=useState<string|null>(()=>path?thumbCache.get(path)??null:null)
const[loading,setLoading]=useState(!!path&&!thumbCache.has(path))
useEffect(()=>{if(!path||!isPyWebView()||thumbCache.has(path)){setLoading(false);return}
getThumbnail(path,type).then(d=>{thumbCache.set(path,d);setSrc(d)}).catch(()=>{}).finally(()=>setLoading(false))},[path,type])
if(!path||(!src&&!loading))return<div className="w-8 h-8 rounded bg-muted flex items-center justify-center shrink-0">{fallback}</div>
if(loading)return<div className="w-8 h-8 rounded bg-muted animate-pulse shrink-0"/>
return<img src={src!} className="w-8 h-8 rounded object-cover shrink-0" alt=""/>}
function CapsuleThumb({path,type,fallback,size=14}:{path?:string;type:ItemType;fallback:React.ReactNode;size?:number}){
const[src,setSrc]=useState<string|null>(()=>path?thumbCache.get(path)??null:null)
useEffect(()=>{if(!path||!isPyWebView()||thumbCache.has(path))return
getThumbnail(path,type).then(d=>{thumbCache.set(path,d);setSrc(d)}).catch(()=>{})},[path,type])
if(!path||!src)return<div className="flex items-center justify-center shrink-0" style={{width:size,height:size}}>{fallback}</div>
return<img src={src} className="rounded-sm object-cover shrink-0" style={{width:size,height:size}} alt=""/>}
export function CapsuleSelector({items,value,onChange,disabled=false,placeholder,emptyLabel,type}:Props){
const[open,setOpen]=useState(false)
const[search,setSearch]=useState('')
const inputRef=useRef<HTMLInputElement>(null)
const selected=items.find(i=>i.slug===value)
const filtered=search?items.filter(i=>i.name.toLowerCase().includes(search.toLowerCase())):items
const Icon=type==='product'?Package:Palette
useEffect(()=>{if(open)setTimeout(()=>inputRef.current?.focus(),50)},[open])
const handleSelect=(slug:string)=>{onChange(slug);setOpen(false);setSearch('')}
return(<DropdownMenu open={open} onOpenChange={o=>{setOpen(o);if(!o)setSearch('')}}>
<DropdownMenuTrigger asChild>
<button type="button" disabled={disabled} className={cn("flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-all","bg-white/50 dark:bg-white/10 border border-border/40","hover:bg-white dark:hover:bg-white/20",disabled&&"opacity-50 cursor-not-allowed","max-w-[140px]")}>
{selected?(<><CapsuleThumb path={selected.imagePath} type={type} fallback={<Icon className="w-3 h-3 opacity-60"/>}/><span className="truncate">{selected.name}</span></>):(<><Icon className="w-3.5 h-3.5 opacity-60"/><span className="truncate text-muted-foreground">{placeholder}</span></>)}
<ChevronDown className="h-3 w-3 opacity-50 shrink-0"/>
</button>
</DropdownMenuTrigger>
<DropdownMenuContent align="start" side="top" sideOffset={8} className="w-64 p-0" onCloseAutoFocus={e=>e.preventDefault()}>
<div className="p-2 border-b border-border/40">
<div className="relative"><Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground"/>
<input ref={inputRef} value={search} onChange={e=>setSearch(e.target.value)} placeholder={`Search ${type}s...`} className="w-full pl-8 pr-3 py-1.5 text-sm bg-transparent border-none outline-none placeholder:text-muted-foreground"/></div>
</div>
<div className="max-h-64 overflow-y-auto p-1.5">
{/* None option */}
<button type="button" onClick={()=>handleSelect('')} className={cn("w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left transition-colors","hover:bg-accent",!value&&"bg-accent")}>
<div className="w-8 h-8 rounded bg-muted flex items-center justify-center shrink-0"><Icon className="w-4 h-4 text-muted-foreground"/></div>
<div className="flex-1 min-w-0"><div className="text-sm font-medium">{emptyLabel}</div></div>
{!value&&<Check className="h-4 w-4 shrink-0"/>}
</button>
{filtered.map(item=>(<button key={item.slug} type="button" onClick={()=>handleSelect(item.slug)} className={cn("w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left transition-colors","hover:bg-accent",value===item.slug&&"bg-accent")}>
<ItemThumb path={item.imagePath} type={type} fallback={<Icon className="w-4 h-4 text-muted-foreground"/>}/>
<div className="flex-1 min-w-0">
<div className="text-sm font-medium truncate">{item.name}</div>
{item.description&&<div className="text-xs text-muted-foreground truncate">{item.description}</div>}
</div>
{value===item.slug&&<Check className="h-4 w-4 shrink-0"/>}
</button>))}
{filtered.length===0&&search&&<div className="py-4 text-center text-sm text-muted-foreground">No {type}s found</div>}
</div>
</DropdownMenuContent>
</DropdownMenu>)}
