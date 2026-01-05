//Autocomplete dropdown for @product: and @style: mentions
import{useState,useEffect,useMemo,useRef,useCallback,forwardRef,useImperativeHandle}from'react'
import{Package,FileImage}from'lucide-react'
import{useProducts}from'@/context/ProductContext'
import{useStyleReferences}from'@/context/StyleReferenceContext'
import{bridge,isPyWebView}from'@/lib/bridge'
import{getCurrentMention}from'@/lib/mentionParser'
import{cn}from'@/lib/utils'
//Thumbnail component for products
function ProdThumb({path}:{path:string}){
const[src,setSrc]=useState<string|null>(null)
useEffect(()=>{
let c=false
async function ld(){
if(!isPyWebView()||!path)return
try{const u=await bridge.getProductImageThumbnail(path);if(!c)setSrc(u)}catch{}}
ld()
return()=>{c=true}},[path])
if(!src)return(<div className="h-6 w-6 rounded bg-muted flex items-center justify-center shrink-0"><Package className="h-3 w-3 text-muted-foreground/50"/></div>)
return<img src={src} alt="" className="h-6 w-6 rounded object-cover shrink-0"/>}
//Thumbnail component for style references
function SrThumb({path}:{path:string}){
const[src,setSrc]=useState<string|null>(null)
useEffect(()=>{
let c=false
async function ld(){
if(!isPyWebView()||!path)return
try{const u=await bridge.getStyleReferenceImageThumbnail(path);if(!c)setSrc(u)}catch{}}
ld()
return()=>{c=true}},[path])
if(!src)return(<div className="h-6 w-6 rounded bg-muted flex items-center justify-center shrink-0"><FileImage className="h-3 w-3 text-muted-foreground/50"/></div>)
return<img src={src} alt="" className="h-6 w-6 rounded object-cover shrink-0"/>}
interface MentionItem{type:'product'|'style';slug:string;name:string;description:string;image:string}
export interface MentionAutocompleteRef{
handleKeyDown:(e:React.KeyboardEvent)=>boolean}
interface MentionAutocompleteProps{
text:string
caretPos:number
onSelect:(type:'product'|'style',slug:string,start:number)=>void
onClose:()=>void}
export const MentionAutocomplete=forwardRef<MentionAutocompleteRef,MentionAutocompleteProps>(
function MentionAutocomplete({text,caretPos,onSelect,onClose},ref){
const{products}=useProducts()
const{styleReferences}=useStyleReferences()
const[hlIdx,setHlIdx]=useState(0)
const listRef=useRef<HTMLDivElement>(null)
//Get current mention context
const mentionCtx=useMemo(()=>getCurrentMention(text,caretPos),[text,caretPos])
//Build filtered items list
const items=useMemo(():MentionItem[]=>{
if(!mentionCtx)return[]
const{query,type}=mentionCtx
const result:MentionItem[]=[]
const q=query.toLowerCase()
if(type==='all'||type==='product'){
for(const p of products){
if(!q||p.name.toLowerCase().includes(q)||p.slug.includes(q)){
result.push({type:'product',slug:p.slug,name:p.name,description:p.description,image:p.primary_image})}}}
if(type==='all'||type==='style'){
for(const sr of styleReferences){
if(!q||sr.name.toLowerCase().includes(q)||sr.slug.includes(q)){
result.push({type:'style',slug:sr.slug,name:sr.name,description:sr.description,image:sr.primary_image})}}}
return result.slice(0,10)},[mentionCtx,products,styleReferences])
//Reset highlight on list change
useEffect(()=>{setHlIdx(0)},[items.length])
//Scroll highlighted into view
useEffect(()=>{
if(!listRef.current)return
const el=listRef.current.querySelector(`[data-idx="${hlIdx}"]`)
el?.scrollIntoView({block:'nearest'})},[hlIdx])
//Handle selection
const selectItem=useCallback((item:MentionItem)=>{
if(!mentionCtx)return
onSelect(item.type,item.slug,mentionCtx.start)},[mentionCtx,onSelect])
//Expose keyboard handler via ref
useImperativeHandle(ref,()=>({
handleKeyDown:(e:React.KeyboardEvent):boolean=>{
//Don't handle during IME composition
if(e.nativeEvent.isComposing)return false
if(!items.length)return false
if(e.key==='ArrowDown'){
e.preventDefault()
setHlIdx(i=>Math.min(i+1,items.length-1))
return true}
if(e.key==='ArrowUp'){
e.preventDefault()
setHlIdx(i=>Math.max(i-1,0))
return true}
if(e.key==='Enter'){
e.preventDefault()
selectItem(items[hlIdx])
return true}
if(e.key==='Escape'){
e.preventDefault()
onClose()
return true}
return false}}),[items,hlIdx,selectItem,onClose])
if(!mentionCtx||items.length===0)return null
return(
<div className="absolute bottom-full left-0 mb-2 w-64 max-h-48 overflow-y-auto rounded-xl border border-border/30 bg-popover shadow-lg z-50" ref={listRef}>
<div className="p-1 space-y-0.5">
{items.map((item,i)=>(
<button key={`${item.type}-${item.slug}`} data-idx={i} type="button" onClick={()=>selectItem(item)} className={cn('w-full flex items-center gap-2 p-1.5 rounded-lg text-left transition-colors',hlIdx===i?'bg-muted':'hover:bg-muted/50')}>
{item.type==='product'?<ProdThumb path={item.image}/>:<SrThumb path={item.image}/>}
<div className="flex-1 min-w-0">
<div className="flex items-center gap-1.5">
<span className="font-medium text-xs truncate">{item.name}</span>
<span className="text-[10px] text-muted-foreground shrink-0">@{item.type}</span>
</div>
{item.description&&<div className="text-[10px] text-muted-foreground truncate">{item.description}</div>}
</div>
</button>))}
</div>
</div>)})
