import { useState, useEffect, useRef } from 'react'
import { Layout, X, Pencil, Lock, Unlock, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ContextMenu, ContextMenuContent, ContextMenuItem, ContextMenuSeparator, ContextMenuTrigger, } from '@/components/ui/context-menu'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useStyleReferences } from '@/context/StyleReferenceContext'
import { useBrand } from '@/context/BrandContext'
import { bridge, isPyWebView, type StyleReferenceSummary } from '@/lib/bridge'
import { CreateStyleReferenceDialog } from '../CreateStyleReferenceDialog'
import { EditStyleReferenceDialog } from '../EditStyleReferenceDialog'
import { StyleReferenceViewModal } from '../StyleReferenceViewModal'
//Thumbnail component for style reference images
function StyleReferenceThumbnail({ path, size = 'sm' }: { path: string; size?: 'sm' | 'lg' }) {
    const [src, setSrc] = useState<string | null>(null)
    useEffect(() => {
        let cancelled = false
        async function load() {
            if (!isPyWebView() || !path) return
            try {
                const dataUrl = size === 'lg' ? await bridge.getStyleReferenceImageFull(path) : await bridge.getStyleReferenceImageThumbnail(path)
                if (!cancelled) setSrc(dataUrl)
            } catch {/*Ignore thumbnail errors*/ }
        }
        load()
        return () => { cancelled = true }
    }, [path, size])
    const sizeClasses = size === 'lg' ? 'h-24 w-24' : 'h-8 w-8'
    if (!src) {
        return (
            <div className={`${sizeClasses} rounded bg-muted flex items-center justify-center shrink-0`}>
                {size === 'lg' ? (<Loader2 className="h-4 w-4 text-muted-foreground animate-spin" />) : (<Layout className="h-4 w-4 text-muted-foreground" />)}
            </div>)
    }
    return <img src={src} alt="" className={`${sizeClasses} rounded object-cover shrink-0 transition-opacity duration-200`} />
}
//Style reference card component
interface StyleReferenceCardProps {styleRef:StyleReferenceSummary;isAttached:boolean;attachedStrict?:boolean;onOpenModal:()=>void;onAttach:()=>void;onDetach:()=>void;onToggleStrict:()=>void;onEdit:()=>void;onDelete:()=>void}
function StyleReferenceCard({styleRef,isAttached,attachedStrict,onOpenModal,onAttach,onDetach,onToggleStrict,onEdit,onDelete}:StyleReferenceCardProps){
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
return(<div><ContextMenu><ContextMenuTrigger asChild><div role="button" tabIndex={0} className={`flex items-center gap-2.5 py-2 px-2.5 rounded-lg cursor-pointer group overflow-hidden transition-all duration-150 hover:translate-x-0.5 ${isAttached?'bg-primary/10 text-foreground shadow-[inset_2px_0_0_0_var(--color-primary)]':'text-muted-foreground/80 hover:bg-muted/50 hover:text-foreground'}`} draggable onDragStart={handleDragStart} onDragEnd={handleDragEnd} onPointerDown={handlePointerDown} onPointerMove={handlePointerMove} onPointerUp={handlePointerUp} onPointerCancel={handlePointerCancel} onClick={handleClick} onKeyDown={handleKeyDown} title="Click to preview, drag to attach to chat"><StyleReferenceThumbnail path={styleRef.primary_image}/><div className="flex-1 min-w-0 overflow-hidden"><div className="flex items-center gap-1.5"><span className={`text-sm truncate ${isAttached?'font-medium text-foreground':'text-foreground/90'}`}>{styleRef.name}</span>{isAttached&&(<span className="flex items-center gap-0.5 shrink-0">{attachedStrict?<Lock className="h-3 w-3 text-primary"/>:<Unlock className="h-3 w-3 text-muted-foreground"/>}</span>)}</div><span className="text-xs text-muted-foreground/70 truncate block">{styleRef.description.length>50?styleRef.description.slice(0,50)+'...':styleRef.description}</span></div></div></ContextMenuTrigger>
<ContextMenuContent>{isAttached?(<><ContextMenuItem onClick={onToggleStrict}>{attachedStrict?<><Unlock className="h-4 w-4 mr-2"/>Allow Variation</>:<><Lock className="h-4 w-4 mr-2"/>Strictly Follow</>}</ContextMenuItem><ContextMenuItem onClick={onDetach}>Detach from Chat</ContextMenuItem></>):(<ContextMenuItem onClick={onAttach}>Attach to Chat</ContextMenuItem>)}<ContextMenuSeparator/><ContextMenuItem onClick={onEdit}><Pencil className="h-4 w-4 mr-2"/>Edit Style Reference</ContextMenuItem><ContextMenuSeparator/><ContextMenuItem onClick={onDelete} className="text-destructive">Delete Style Reference</ContextMenuItem></ContextMenuContent></ContextMenu></div>)}
interface StyleReferencesSectionProps { createDialogOpen?: boolean; onCreateDialogChange?: (open: boolean) => void }
//Main section component
export function StyleReferencesSection({ createDialogOpen, onCreateDialogChange }: StyleReferencesSectionProps = {}) {
const { activeBrand } = useBrand()
const { styleReferences, attachedStyleReferences, isLoading, error, refresh, attachStyleReference, detachStyleReference, setStyleReferenceStrictness, deleteStyleReference } = useStyleReferences()
const [actionError,setActionError]=useState<string|null>(null)
const [localCreateDialogOpen,setLocalCreateDialogOpen]=useState(false)
const isCreateDialogOpen=createDialogOpen??localCreateDialogOpen
const setIsCreateDialogOpen=onCreateDialogChange??setLocalCreateDialogOpen
const [viewingStyleRefSlug,setViewingStyleRefSlug]=useState<string|null>(null)
const [editingStyleRefSlug,setEditingStyleRefSlug]=useState<string|null>(null)
useEffect(()=>{if(actionError){const t=setTimeout(()=>setActionError(null),5000);return()=>clearTimeout(t)}},[actionError])
const handleToggleStrict=(slug:string)=>{const attached=attachedStyleReferences.find(t=>t.style_reference_slug===slug);if(attached)setStyleReferenceStrictness(slug,!attached.strict)}
const handleDelete=async(slug:string)=>{if(confirm(`Delete style reference "${slug}"? This cannot be undone.`)){try{await deleteStyleReference(slug)}catch(err){setActionError(err instanceof Error?err.message:'Failed to delete style reference')}}}
if(!activeBrand){return<div className="text-sm text-muted-foreground">Select a brand</div>}
if(error){return(<div className="text-sm text-destructive">Error: {error}<Button variant="ghost" size="sm" onClick={refresh}>Retry</Button></div>)}
return(
<div className="space-y-1 pl-1 pr-1">{actionError&&(<Alert variant="destructive" className="py-2 px-3 mb-2"><AlertDescription className="flex items-center justify-between text-xs"><span>{actionError}</span><Button variant="ghost" size="icon" className="h-4 w-4 shrink-0" onClick={()=>setActionError(null)}><X className="h-3 w-3"/></Button></AlertDescription></Alert>)}{styleReferences.length===0?(<p className="text-xs text-muted-foreground py-2 px-2">{isLoading?'Loading...':'No style references yet. Click + to add one.'}</p>):(<div className="space-y-0.5">{styleReferences.map((sr)=>{const attached=attachedStyleReferences.find(t=>t.style_reference_slug===sr.slug);return(<StyleReferenceCard key={sr.slug} styleRef={sr} isAttached={!!attached} attachedStrict={attached?.strict} onOpenModal={()=>setViewingStyleRefSlug(sr.slug)} onAttach={()=>attachStyleReference(sr.slug)} onDetach={()=>detachStyleReference(sr.slug)} onToggleStrict={()=>handleToggleStrict(sr.slug)} onEdit={()=>setEditingStyleRefSlug(sr.slug)} onDelete={()=>handleDelete(sr.slug)}/>)})}</div>)}
<CreateStyleReferenceDialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}/>
{viewingStyleRefSlug&&(<StyleReferenceViewModal open={!!viewingStyleRefSlug} onOpenChange={(o)=>{if(!o)setViewingStyleRefSlug(null)}} styleRefSlug={viewingStyleRefSlug} onEdit={(slug)=>{setViewingStyleRefSlug(null);setEditingStyleRefSlug(slug)}} onDelete={handleDelete}/>)}
{editingStyleRefSlug&&(<EditStyleReferenceDialog open={!!editingStyleRefSlug} onOpenChange={(o)=>{if(!o)setEditingStyleRefSlug(null)}} styleRefSlug={editingStyleRefSlug}/>)}</div>)}
