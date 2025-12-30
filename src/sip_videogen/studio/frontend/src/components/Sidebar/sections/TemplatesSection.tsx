import { useState, useEffect } from 'react'
import { Layout, X, Star, Pencil, ChevronRight, ChevronDown, Loader2, Lock, Unlock } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ContextMenu, ContextMenuContent, ContextMenuItem, ContextMenuSeparator, ContextMenuTrigger, } from '@/components/ui/context-menu'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useTemplates } from '@/context/TemplateContext'
import { useBrand } from '@/context/BrandContext'
import { bridge, isPyWebView, type TemplateSummary, type TemplateFull } from '@/lib/bridge'
import { CreateTemplateDialog } from '../CreateTemplateDialog'
import { EditTemplateDialog } from '../EditTemplateDialog'
import { TemplateDetailView } from '../TemplateDetailView'
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
    return <img src={src} alt="" className={`${sizeClasses} rounded object-cover shrink-0`} />
}
//Preview component for expanded template view
interface TemplatePreviewProps { templateSlug: string }
function TemplatePreview({ templateSlug }: TemplatePreviewProps) {
    const { getTemplate, getTemplateImages } = useTemplates()
    const [template, setTemplate] = useState<TemplateFull | null>(null)
    const [images, setImages] = useState<string[]>([])
    const [isLoading, setIsLoading] = useState(true)
    useEffect(() => {
        let cancelled = false
        async function load() {
            setIsLoading(true)
            try {
                const [templateData, imagePaths] = await Promise.all([getTemplate(templateSlug), getTemplateImages(templateSlug)])
                if (!cancelled) { setTemplate(templateData); setImages(imagePaths) }
            } catch (err) {
                console.error('Failed to load template preview:', err)
            } finally { if (!cancelled) setIsLoading(false) }
        }
        load()
        return () => { cancelled = true }
    }, [templateSlug, getTemplate, getTemplateImages])
    if (isLoading) {
        return (
            <div className="py-3 flex items-center gap-2 text-xs text-muted-foreground">
                <Loader2 className="h-3 w-3 animate-spin" />Loading...</div>)
    }
    if (!template) { return (<div className="py-2 text-xs text-destructive">Failed to load template</div>) }
    return (
        <div className="py-3 space-y-3">
            {/*Image Gallery*/}
            {images.length > 0 && (
                <div className="flex flex-wrap gap-2">
                    {images.map((path, index) => (
                        <div key={path} className={`relative rounded-md overflow-hidden ${path === template.primary_image ? 'ring-2 ring-primary ring-offset-2' : 'ring-1 ring-border/50'}`}>
                            <TemplateThumbnail path={path} size="lg" />
                            {path === template.primary_image && (
                                <div className="absolute top-1 left-1 bg-primary text-primary-foreground rounded-full p-0.5 shadow-sm">
                                    <Star className="h-2.5 w-2.5 fill-current" /></div>)}
                            {index === 0 && images.length > 1 && (
                                <span className="absolute bottom-1 right-1 bg-black/60 text-white text-[10px] px-1.5 py-0.5 rounded backdrop-blur-sm">1/{images.length}</span>)}
                        </div>))}
                </div>)}
            {/*Description*/}
            {template.description && (
                <div className="space-y-1">
                    <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">Description</span>
                    <p className="text-xs text-foreground/80 whitespace-pre-wrap">{template.description}</p>
                </div>)}
            {/*Default strictness and stats*/}
            <div className="flex items-center gap-3 text-[10px] text-muted-foreground pt-1 border-t border-border">
                <span className="flex items-center gap-1">
                    {template.default_strict ? <Lock className="h-3 w-3" /> : <Unlock className="h-3 w-3" />}
                    {template.default_strict ? 'Strict by default' : 'Loose by default'}</span>
                <span>{images.length} image{images.length !== 1 ? 's' : ''}</span>
            </div>
        </div>)
}
//Template card component
interface TemplateCardProps {
    template: TemplateSummary
    isAttached: boolean
    attachedStrict?: boolean
    isExpanded: boolean
    onToggleExpand: () => void
    onAttach: () => void
    onDetach: () => void
    onToggleStrict: () => void
    onViewDetail: () => void
    onEdit: () => void
    onDelete: () => void
}
function TemplateCard({ template, isAttached, attachedStrict, isExpanded, onToggleExpand, onAttach, onDetach, onToggleStrict, onViewDetail, onEdit, onDelete }: TemplateCardProps) {
    const handleDragStart = (e: React.DragEvent) => {
        e.dataTransfer.setData('text/plain', template.slug)
        try { e.dataTransfer.setData('application/x-brand-template', template.slug) } catch {/*ignore*/ }
        e.dataTransfer.effectAllowed = 'copy'
    }
    const handleClick = (e: React.MouseEvent) => {
        if (e.defaultPrevented) return
        onToggleExpand()
    }
    return (
        <div><ContextMenu><ContextMenuTrigger asChild><div className={`flex items-center gap-2.5 py-2 px-2.5 rounded-lg cursor-pointer group overflow-hidden transition-colors duration-150 ${isAttached?'bg-primary/10 text-foreground':'text-muted-foreground/80 hover:bg-muted/50 hover:text-foreground'}`} draggable onDragStart={handleDragStart} onClick={handleClick} title="Click to preview, drag to attach to chat">{isExpanded?(<ChevronDown className="h-3.5 w-3.5 shrink-0 text-muted-foreground/70"/>):(<ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground/70 group-hover:text-foreground/80 transition-colors duration-150"/>)}<TemplateThumbnail path={template.primary_image}/><div className="flex-1 min-w-0 overflow-hidden"><div className="flex items-center gap-1.5"><span className={`text-sm truncate ${isAttached?'font-medium text-foreground':'text-foreground/90'}`}>{template.name}</span>{isAttached&&(<span className="flex items-center gap-0.5 shrink-0">{attachedStrict?<Lock className="h-3 w-3 text-primary"/>:<Unlock className="h-3 w-3 text-muted-foreground"/>}</span>)}</div><span className="text-xs text-muted-foreground/70 truncate block">{template.description.length>50?template.description.slice(0,50)+'...':template.description}</span></div></div></ContextMenuTrigger>
                <ContextMenuContent>
                    {isAttached ? (
                        <>
                            <ContextMenuItem onClick={onToggleStrict}>
                                {attachedStrict ? <><Unlock className="h-4 w-4 mr-2" />Allow Variation</> : <><Lock className="h-4 w-4 mr-2" />Strictly Follow</>}
                            </ContextMenuItem>
                            <ContextMenuItem onClick={onDetach}>Detach from Chat</ContextMenuItem>
                        </>) : (
                        <ContextMenuItem onClick={onAttach}>Attach to Chat</ContextMenuItem>)}
                    <ContextMenuSeparator />
                    <ContextMenuItem onClick={onViewDetail}><Layout className="h-4 w-4 mr-2" />View Details</ContextMenuItem>
                    <ContextMenuItem onClick={onEdit}><Pencil className="h-4 w-4 mr-2" />Edit Template</ContextMenuItem>
                    <ContextMenuSeparator />
                    <ContextMenuItem onClick={onDelete} className="text-destructive">Delete Template</ContextMenuItem>
                </ContextMenuContent>
            </ContextMenu>
            {/*Expanded preview*/}
            {isExpanded&&(<div className="pl-6 pr-2 border-l border-border/30 ml-[11px] mt-1 relative"><div className="absolute top-0 -left-[3px] w-1.5 h-1.5 rounded-full bg-border/50"></div><TemplatePreview templateSlug={template.slug}/></div>)}</div>)}
interface TemplatesSectionProps { createDialogOpen?: boolean; onCreateDialogChange?: (open: boolean) => void }
//Main section component
export function TemplatesSection({ createDialogOpen, onCreateDialogChange }: TemplatesSectionProps = {}) {
    const { activeBrand } = useBrand()
    const { templates, attachedTemplates, isLoading, error, refresh, attachTemplate, detachTemplate, setTemplateStrictness, deleteTemplate } = useTemplates()
    const [actionError, setActionError] = useState<string | null>(null)
    const [localCreateDialogOpen, setLocalCreateDialogOpen] = useState(false)
    const isCreateDialogOpen = createDialogOpen ?? localCreateDialogOpen
    const setIsCreateDialogOpen = onCreateDialogChange ?? setLocalCreateDialogOpen
    const [editingTemplateSlug, setEditingTemplateSlug] = useState<string | null>(null)
    const [expandedTemplate, setExpandedTemplate] = useState<string | null>(null)
    const [detailViewSlug, setDetailViewSlug] = useState<string | null>(null)
    useEffect(() => {
        if (actionError) { const timer = setTimeout(() => setActionError(null), 5000); return () => clearTimeout(timer) }
    }, [actionError])
    const handleToggleExpand = (slug: string) => { setExpandedTemplate(prev => prev === slug ? null : slug) }
    const handleToggleStrict = (slug: string) => {
        const attached = attachedTemplates.find(t => t.template_slug === slug)
        if (attached) setTemplateStrictness(slug, !attached.strict)
    }
    const handleDelete = async (slug: string) => {
        if (confirm(`Delete template "${slug}"? This cannot be undone.`)) {
            try { await deleteTemplate(slug); if (expandedTemplate === slug) setExpandedTemplate(null); if (detailViewSlug === slug) setDetailViewSlug(null) }
            catch (err) { setActionError(err instanceof Error ? err.message : 'Failed to delete template') }
        }
    }
    const handleOpenDetail = (slug: string) => { setDetailViewSlug(slug); setExpandedTemplate(null) }
    if (!activeBrand) { return <div className="text-sm text-muted-foreground">Select a brand</div> }
    if (error) {
        return (
            <div className="text-sm text-destructive">
                Error: {error}
                <Button variant="ghost" size="sm" onClick={refresh}>Retry</Button>
            </div>)
    }
    return (
        <div className="space-y-1 pl-1 pr-1">{actionError&&(<Alert variant="destructive" className="py-2 px-3 mb-2"><AlertDescription className="flex items-center justify-between text-xs"><span>{actionError}</span><Button variant="ghost" size="icon" className="h-4 w-4 shrink-0" onClick={()=>setActionError(null)}><X className="h-3 w-3"/></Button></AlertDescription></Alert>)}{templates.length===0?(<p className="text-xs text-muted-foreground py-2 px-2">{isLoading?'Loading...':'No templates yet. Click + to add one.'}</p>):(<div className="space-y-0.5">{templates.map((template)=>{const attached=attachedTemplates.find(t=>t.template_slug===template.slug);return(<TemplateCard key={template.slug} template={template} isAttached={!!attached} attachedStrict={attached?.strict} isExpanded={expandedTemplate===template.slug} onToggleExpand={()=>handleToggleExpand(template.slug)} onAttach={()=>attachTemplate(template.slug)} onDetach={()=>detachTemplate(template.slug)} onToggleStrict={()=>handleToggleStrict(template.slug)} onViewDetail={()=>handleOpenDetail(template.slug)} onEdit={()=>setEditingTemplateSlug(template.slug)} onDelete={()=>handleDelete(template.slug)}/>)})}</div>)}
            {/*Detail View Modal*/}
            {detailViewSlug && (<div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={() => setDetailViewSlug(null)}>
                <div className="bg-background border rounded-lg shadow-xl max-w-md w-full max-h-[80vh] overflow-auto" onClick={e => e.stopPropagation()}>
                    <TemplateDetailView templateSlug={detailViewSlug}
                        onEdit={() => { setEditingTemplateSlug(detailViewSlug); setDetailViewSlug(null) }}
                        onDelete={() => setDetailViewSlug(null)}
                        onClose={() => setDetailViewSlug(null)} />
                </div>
            </div>)}
            <CreateTemplateDialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen} />
            {editingTemplateSlug && <EditTemplateDialog open={!!editingTemplateSlug} onOpenChange={(open) => { if (!open) setEditingTemplateSlug(null) }} templateSlug={editingTemplateSlug} />}
        </div>)
}
