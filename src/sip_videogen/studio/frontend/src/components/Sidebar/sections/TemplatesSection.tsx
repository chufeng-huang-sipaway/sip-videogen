import { useState, useEffect, useRef } from 'react'
import { Layout, X, Pencil, Lock, Unlock, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ContextMenu, ContextMenuContent, ContextMenuItem, ContextMenuSeparator, ContextMenuTrigger, } from '@/components/ui/context-menu'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useTemplates } from '@/context/TemplateContext'
import { useBrand } from '@/context/BrandContext'
import { bridge, isPyWebView, type TemplateSummary } from '@/lib/bridge'
import { CreateTemplateDialog } from '../CreateTemplateDialog'
import { EditTemplateDialog } from '../EditTemplateDialog'
import { TemplateModal } from '../TemplateModal'
//Thumbnail component for template images
function TemplateThumbnail({ path, size = 'sm' }: { path: string; size?: 'sm' | 'lg' }) {
    const [src, setSrc] = useState<string | null>(null)
    useEffect(() => {
        let cancelled = false
        async function load() {
            if (!isPyWebView() || !path) return
            try {
                const dataUrl = size === 'lg' ? await bridge.getTemplateImageFull(path) : await bridge.getTemplateImageThumbnail(path)
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
//Template card component
interface TemplateCardProps {template:TemplateSummary;isAttached:boolean;attachedStrict?:boolean;onOpenModal:()=>void;onAttach:()=>void;onDetach:()=>void;onToggleStrict:()=>void;onEdit:()=>void;onDelete:()=>void}
function TemplateCard({template,isAttached,attachedStrict,onOpenModal,onAttach,onDetach,onToggleStrict,onEdit,onDelete}:TemplateCardProps){
const didDragRef=useRef(false)
const pointerStartRef=useRef<{x:number;y:number}|null>(null)
const handlePointerDown=(e:React.PointerEvent)=>{pointerStartRef.current={x:e.clientX,y:e.clientY};didDragRef.current=false}
const handlePointerMove=(e:React.PointerEvent)=>{if(!pointerStartRef.current)return;const dx=Math.abs(e.clientX-pointerStartRef.current.x);const dy=Math.abs(e.clientY-pointerStartRef.current.y);if(dx>5||dy>5)didDragRef.current=true}
const handlePointerUp=()=>{pointerStartRef.current=null}
const handlePointerCancel=()=>{pointerStartRef.current=null;didDragRef.current=false}
const handleDragStart=(e:React.DragEvent)=>{didDragRef.current=true;e.dataTransfer.setData('text/plain',template.slug);try{e.dataTransfer.setData('application/x-brand-template',template.slug)}catch{};e.dataTransfer.effectAllowed='copy'}
const handleDragEnd=()=>{setTimeout(()=>{didDragRef.current=false},0)}
const handleClick=()=>{if(didDragRef.current){didDragRef.current=false;return};onOpenModal()}
const handleKeyDown=(e:React.KeyboardEvent)=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();onOpenModal()}}
return(<div><ContextMenu><ContextMenuTrigger asChild><div role="button" tabIndex={0} className={`flex items-center gap-2.5 py-2 px-2.5 rounded-lg cursor-pointer group overflow-hidden transition-all duration-150 hover:translate-x-0.5 ${isAttached?'bg-primary/10 text-foreground shadow-[inset_2px_0_0_0_var(--color-primary)]':'text-muted-foreground/80 hover:bg-muted/50 hover:text-foreground'}`} draggable onDragStart={handleDragStart} onDragEnd={handleDragEnd} onPointerDown={handlePointerDown} onPointerMove={handlePointerMove} onPointerUp={handlePointerUp} onPointerCancel={handlePointerCancel} onClick={handleClick} onKeyDown={handleKeyDown} title="Click to preview, drag to attach to chat"><TemplateThumbnail path={template.primary_image}/><div className="flex-1 min-w-0 overflow-hidden"><div className="flex items-center gap-1.5"><span className={`text-sm truncate ${isAttached?'font-medium text-foreground':'text-foreground/90'}`}>{template.name}</span>{isAttached&&(<span className="flex items-center gap-0.5 shrink-0">{attachedStrict?<Lock className="h-3 w-3 text-primary"/>:<Unlock className="h-3 w-3 text-muted-foreground"/>}</span>)}</div><span className="text-xs text-muted-foreground/70 truncate block">{template.description.length>50?template.description.slice(0,50)+'...':template.description}</span></div></div></ContextMenuTrigger>
<ContextMenuContent>{isAttached?(<><ContextMenuItem onClick={onToggleStrict}>{attachedStrict?<><Unlock className="h-4 w-4 mr-2"/>Allow Variation</>:<><Lock className="h-4 w-4 mr-2"/>Strictly Follow</>}</ContextMenuItem><ContextMenuItem onClick={onDetach}>Detach from Chat</ContextMenuItem></>):(<ContextMenuItem onClick={onAttach}>Attach to Chat</ContextMenuItem>)}<ContextMenuSeparator/><ContextMenuItem onClick={onEdit}><Pencil className="h-4 w-4 mr-2"/>Edit Template</ContextMenuItem><ContextMenuSeparator/><ContextMenuItem onClick={onDelete} className="text-destructive">Delete Template</ContextMenuItem></ContextMenuContent></ContextMenu></div>)}
interface TemplatesSectionProps { createDialogOpen?: boolean; onCreateDialogChange?: (open: boolean) => void }
//Main section component
export function TemplatesSection({ createDialogOpen, onCreateDialogChange }: TemplatesSectionProps = {}) {
const { activeBrand } = useBrand()
const { templates, attachedTemplates, isLoading, error, refresh, attachTemplate, detachTemplate, setTemplateStrictness, deleteTemplate } = useTemplates()
const [actionError,setActionError]=useState<string|null>(null)
const [localCreateDialogOpen,setLocalCreateDialogOpen]=useState(false)
const isCreateDialogOpen=createDialogOpen??localCreateDialogOpen
const setIsCreateDialogOpen=onCreateDialogChange??setLocalCreateDialogOpen
const [editingTemplateSlug,setEditingTemplateSlug]=useState<string|null>(null)
const [modalSlug,setModalSlug]=useState<string|null>(null)
useEffect(()=>{if(actionError){const t=setTimeout(()=>setActionError(null),5000);return()=>clearTimeout(t)}},[actionError])
const handleToggleStrict=(slug:string)=>{const attached=attachedTemplates.find(t=>t.template_slug===slug);if(attached)setTemplateStrictness(slug,!attached.strict)}
const handleEditFromModal=(slug:string)=>{setModalSlug(null);requestAnimationFrame(()=>{setEditingTemplateSlug(slug)})}
const handleDeleteFromModal=async(slug:string)=>{setModalSlug(null);requestAnimationFrame(async()=>{if(confirm(`Delete template "${slug}"? This cannot be undone.`)){try{await deleteTemplate(slug)}catch(err){setActionError(err instanceof Error?err.message:'Failed to delete template')}}})}
const handleDelete=async(slug:string)=>{if(confirm(`Delete template "${slug}"? This cannot be undone.`)){try{await deleteTemplate(slug);if(modalSlug===slug)setModalSlug(null)}catch(err){setActionError(err instanceof Error?err.message:'Failed to delete template')}}}
if(!activeBrand){return<div className="text-sm text-muted-foreground">Select a brand</div>}
if(error){return(<div className="text-sm text-destructive">Error: {error}<Button variant="ghost" size="sm" onClick={refresh}>Retry</Button></div>)}
return(
<div className="space-y-1 pl-1 pr-1">{actionError&&(<Alert variant="destructive" className="py-2 px-3 mb-2"><AlertDescription className="flex items-center justify-between text-xs"><span>{actionError}</span><Button variant="ghost" size="icon" className="h-4 w-4 shrink-0" onClick={()=>setActionError(null)}><X className="h-3 w-3"/></Button></AlertDescription></Alert>)}{templates.length===0?(<p className="text-xs text-muted-foreground py-2 px-2">{isLoading?'Loading...':'No templates yet. Click + to add one.'}</p>):(<div className="space-y-0.5">{templates.map((template)=>{const attached=attachedTemplates.find(t=>t.template_slug===template.slug);return(<TemplateCard key={template.slug} template={template} isAttached={!!attached} attachedStrict={attached?.strict} onOpenModal={()=>setModalSlug(template.slug)} onAttach={()=>attachTemplate(template.slug)} onDetach={()=>detachTemplate(template.slug)} onToggleStrict={()=>handleToggleStrict(template.slug)} onEdit={()=>setEditingTemplateSlug(template.slug)} onDelete={()=>handleDelete(template.slug)}/>)})}</div>)}
<TemplateModal slug={modalSlug} onClose={()=>setModalSlug(null)} onEdit={handleEditFromModal} onDelete={handleDeleteFromModal}/>
<CreateTemplateDialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}/>
{editingTemplateSlug&&(<EditTemplateDialog open={!!editingTemplateSlug} onOpenChange={(o)=>{if(!o)setEditingTemplateSlug(null)}} templateSlug={editingTemplateSlug}/>)}</div>)}
