import{useState,useEffect,useRef}from'react'
import{Layout,X,Pencil,Loader2}from'lucide-react'
import{Button}from'@/components/ui/button'
import{ContextMenu,ContextMenuContent,ContextMenuItem,ContextMenuSeparator,ContextMenuTrigger}from'@/components/ui/context-menu'
import{Alert,AlertDescription}from'@/components/ui/alert'
import{useStyleReferences}from'@/context/StyleReferenceContext'
import{useBrand}from'@/context/BrandContext'
import{bridge,isPyWebView,type StyleReferenceSummary}from'@/lib/bridge'
import{QuickCreateStyleReferenceDialog}from'../QuickCreateStyleReferenceDialog'
import{UnifiedStyleReferenceModal}from'../UnifiedStyleReferenceModal'
//Thumbnail component
function StyleReferenceThumbnail({path,size='sm'}:{path:string;size?:'sm'|'lg'}){
const[src,setSrc]=useState<string|null>(null)
useEffect(()=>{let cancelled=false
async function load(){if(!isPyWebView()||!path)return
try{const dataUrl=size==='lg'?await bridge.getStyleReferenceImageFull(path):await bridge.getStyleReferenceImageThumbnail(path);if(!cancelled)setSrc(dataUrl)}catch{}}
load();return()=>{cancelled=true}},[path,size])
const sizeClasses=size==='lg'?'h-24 w-24':'h-8 w-8'
if(!src)return(<div className={`${sizeClasses} rounded bg-muted flex items-center justify-center shrink-0`}>{size==='lg'?<Loader2 className="h-4 w-4 text-muted-foreground animate-spin"/>:<Layout className="h-4 w-4 text-muted-foreground"/>}</div>)
return<img src={src} alt="" className={`${sizeClasses} rounded object-cover shrink-0 transition-opacity duration-200`}/>}
//Style reference card
interface StyleReferenceCardProps{styleRef:StyleReferenceSummary;isAttached:boolean;onOpenModal:()=>void;onOpenEdit:()=>void;onAttach:()=>void;onDetach:()=>void;onDelete:()=>void}
function StyleReferenceCard({styleRef,isAttached,onOpenModal,onOpenEdit,onAttach,onDetach,onDelete}:StyleReferenceCardProps){
const didDragRef=useRef(false)
const pointerStartRef=useRef<{x:number;y:number}|null>(null)
const handlePointerDown=(e:React.PointerEvent)=>{pointerStartRef.current={x:e.clientX,y:e.clientY};didDragRef.current=false}
const handlePointerMove=(e:React.PointerEvent)=>{if(!pointerStartRef.current)return;const dx=Math.abs(e.clientX-pointerStartRef.current.x);const dy=Math.abs(e.clientY-pointerStartRef.current.y);if(dx>5||dy>5)didDragRef.current=true}
const handlePointerUp=()=>{pointerStartRef.current=null}
const handlePointerCancel=()=>{pointerStartRef.current=null;didDragRef.current=false}
const handleDragStart=(e:React.DragEvent)=>{didDragRef.current=true;e.dataTransfer.setData('text/plain',styleRef.slug);try{e.dataTransfer.setData('application/x-brand-style-reference',styleRef.slug)}catch{};e.dataTransfer.effectAllowed='copy'}
const handleDragEnd=()=>{setTimeout(()=>{didDragRef.current=false},0)}
const handleClick=()=>{if(didDragRef.current){didDragRef.current=false;return};onOpenModal()}
const handleKeyDown=(e:React.KeyboardEvent)=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();onOpenModal()}}
return(<div><ContextMenu><ContextMenuTrigger asChild><div role="button" tabIndex={0} className={`flex items-center gap-2.5 py-2 px-2.5 rounded-lg cursor-pointer group overflow-hidden transition-all duration-150 hover:translate-x-0.5 ${isAttached?'bg-primary/10 text-foreground shadow-[inset_2px_0_0_0_var(--color-primary)]':'text-muted-foreground/80 hover:bg-muted/50 hover:text-foreground'}`} draggable onDragStart={handleDragStart} onDragEnd={handleDragEnd} onPointerDown={handlePointerDown} onPointerMove={handlePointerMove} onPointerUp={handlePointerUp} onPointerCancel={handlePointerCancel} onClick={handleClick} onKeyDown={handleKeyDown} title="Click to preview, drag to attach to chat"><StyleReferenceThumbnail path={styleRef.primary_image}/><div className="flex-1 min-w-0 overflow-hidden"><span className={`text-sm truncate block ${isAttached?'font-medium text-foreground':'text-foreground/90'}`}>{styleRef.name}</span><span className="text-xs text-muted-foreground/70 truncate block">{styleRef.description.length>50?styleRef.description.slice(0,50)+'...':styleRef.description}</span></div></div></ContextMenuTrigger>
<ContextMenuContent>{isAttached?(<ContextMenuItem onClick={onDetach}>Detach from Chat</ContextMenuItem>):(<ContextMenuItem onClick={onAttach}>Attach to Chat</ContextMenuItem>)}<ContextMenuSeparator/><ContextMenuItem onClick={onOpenEdit}><Pencil className="h-4 w-4 mr-2"/>Edit</ContextMenuItem><ContextMenuSeparator/><ContextMenuItem onClick={onDelete} className="text-destructive">Delete</ContextMenuItem></ContextMenuContent></ContextMenu></div>)}
interface StyleReferencesSectionProps{createDialogOpen?:boolean;onCreateDialogChange?:(open:boolean)=>void}
//Main section component
export function StyleReferencesSection({createDialogOpen,onCreateDialogChange}:StyleReferencesSectionProps={}){
const{activeBrand}=useBrand()
const{styleReferences,attachedStyleReferences,isLoading,error,refresh,attachStyleReference,detachStyleReference,deleteStyleReference}=useStyleReferences()
const[actionError,setActionError]=useState<string|null>(null)
//Unified state: single modal with mode
const[activeStyleRefSlug,setActiveStyleRefSlug]=useState<string|null>(null)
const[modalMode,setModalMode]=useState<'view'|'edit'|null>(null)
//Quick create dialog
const[localCreateDialogOpen,setLocalCreateDialogOpen]=useState(false)
const isQuickCreateOpen=createDialogOpen??localCreateDialogOpen
const setIsQuickCreateOpen=onCreateDialogChange??setLocalCreateDialogOpen
//Clear action errors after timeout
useEffect(()=>{if(actionError){const t=setTimeout(()=>setActionError(null),5000);return()=>clearTimeout(t)}},[actionError])
//Handlers
const openViewModal=(slug:string)=>{setActiveStyleRefSlug(slug);setModalMode('view')}
const openEditModal=(slug:string)=>{setActiveStyleRefSlug(slug);setModalMode('edit')}
const closeModal=()=>{setActiveStyleRefSlug(null);setModalMode(null)}
//Quick create callback - auto-opens view modal
const handleQuickCreateDone=(slug:string)=>{setIsQuickCreateOpen(false);openViewModal(slug)}
const handleDelete=async(slug:string)=>{if(confirm(`Delete style reference "${slug}"? This cannot be undone.`)){try{await deleteStyleReference(slug);closeModal()}catch(err){setActionError(err instanceof Error?err.message:'Failed to delete')}}}
if(!activeBrand)return<div className="text-sm text-muted-foreground">Select a brand</div>
if(error)return(<div className="text-sm text-destructive">Error: {error}<Button variant="ghost" size="sm" onClick={refresh}>Retry</Button></div>)
return(
<div className="space-y-1 pl-1 pr-1">
{actionError&&(<Alert variant="destructive" className="py-2 px-3 mb-2"><AlertDescription className="flex items-center justify-between text-xs"><span>{actionError}</span><Button variant="ghost" size="icon" className="h-4 w-4 shrink-0" onClick={()=>setActionError(null)}><X className="h-3 w-3"/></Button></AlertDescription></Alert>)}
{styleReferences.length===0?(<p className="text-xs text-muted-foreground py-2 px-2">{isLoading?'Loading...':'No style references yet. Click + to add one.'}</p>):(<div className="space-y-0.5">{styleReferences.map(sr=>{const isAttached=attachedStyleReferences.some(t=>t.style_reference_slug===sr.slug);return(<StyleReferenceCard key={sr.slug} styleRef={sr} isAttached={isAttached} onOpenModal={()=>openViewModal(sr.slug)} onOpenEdit={()=>openEditModal(sr.slug)} onAttach={()=>attachStyleReference(sr.slug)} onDetach={()=>detachStyleReference(sr.slug)} onDelete={()=>handleDelete(sr.slug)}/>)})}</div>)}
{/*Quick Create Dialog*/}
<QuickCreateStyleReferenceDialog open={isQuickCreateOpen} onOpenChange={setIsQuickCreateOpen} onCreated={handleQuickCreateDone}/>
{/*Unified Modal - View or Edit mode*/}
{activeStyleRefSlug&&(<UnifiedStyleReferenceModal open={!!activeStyleRefSlug} onOpenChange={o=>{if(!o)closeModal()}} styleRefSlug={activeStyleRefSlug} initialMode={modalMode||'view'} onDelete={handleDelete}/>)}
</div>)}
