//Workstation component - image review and curation workspace
import { useCallback, useRef, useEffect, useMemo } from 'react'
import { useWorkstation, type GeneratedImage } from '../../context/WorkstationContext'
import { useBrand } from '../../context/BrandContext'
import { bridge, waitForPyWebViewReady, type ImageStatusEntry } from '../../lib/bridge'
import { toast } from '../ui/toaster'
import { ImageDisplay } from './ImageDisplay'
import { ThumbnailStrip } from './ThumbnailStrip'
import { SwipeContainer } from './SwipeContainer'
import { EmptyState } from './EmptyState'
import { ComparisonView } from './ComparisonView'
import { ContextPanel } from './ContextPanel'
import { ExportActions } from './ExportActions'
import { TrashView } from './TrashView'
import { Button } from '../ui/button'
import { Trash2, Heart, LayoutGrid, Image as ImageIcon } from 'lucide-react'
import { Tooltip, TooltipContent, TooltipTrigger } from '../ui/tooltip'
import { ImageGrid } from './ImageGrid'
import { cn } from '@/lib/utils'

export function Workstation() {
    const { currentBatch, selectedIndex, viewMode, setViewMode, setCurrentBatch, setSelectedIndex, removeFromUnsorted, addToUnsorted, isTrashView, setIsTrashView, bumpStatusVersion, browseMode, setBrowseMode } = useWorkstation()
    const { activeBrand } = useBrand()

    const hasImages = currentBatch.length > 0
    const currentImage = currentBatch[selectedIndex]
    const isComparison = viewMode === 'comparison'
    const isKept = currentImage?.status === 'kept'
    const lastToastId = useRef<string | number | undefined>(undefined)

    const filename = useMemo(() => {
        const p = currentImage?.originalPath || currentImage?.path;
        if (!p || p.startsWith('data:')) return '';
        const parts = p.split('/');
        return parts[parts.length - 1] || ''
    }, [currentImage?.originalPath, currentImage?.path])

    const imageCounter = `${selectedIndex + 1} / ${currentBatch.length}`

    //Load unsorted backlog on brand change
    useEffect(() => {
        let cancelled = false
        async function loadUnsorted() {
            if (!activeBrand) { setCurrentBatch([]); setIsTrashView(false); return }
            const ready = await waitForPyWebViewReady()
            if (!ready || cancelled) return
            try {
                const images = await bridge.getUnsortedImages(activeBrand); if (cancelled) return
                const batch = images.map((img: ImageStatusEntry) => ({ id: img.id, path: img.currentPath, prompt: img.prompt || undefined, sourceTemplatePath: img.sourceTemplatePath || undefined, timestamp: img.timestamp }))
                setCurrentBatch(batch)
            } catch (e) { console.error('Failed to load unsorted images:', e) }
        }
        loadUnsorted()
        return () => { cancelled = true }
    }, [activeBrand, setCurrentBatch, setIsTrashView])

    //Exit trash view
    const handleExitTrash = useCallback(() => { setIsTrashView(false); setCurrentBatch([]) }, [setIsTrashView, setCurrentBatch])

    const toggleComparison = useCallback(() => { setViewMode(isComparison ? 'single' : 'comparison') }, [isComparison, setViewMode])

    const isGrid = browseMode === 'grid'
    const toggleBrowseMode = useCallback(() => { setBrowseMode(isGrid ? 'preview' : 'grid') }, [isGrid, setBrowseMode])

    const removeCurrentAndAdvance = useCallback(() => { const newBatch = [...currentBatch]; newBatch.splice(selectedIndex, 1); setCurrentBatch(newBatch); if (selectedIndex >= newBatch.length && newBatch.length > 0) setSelectedIndex(newBatch.length - 1) }, [currentBatch, selectedIndex, setCurrentBatch, setSelectedIndex])

    const undoKeep = useCallback(async (image: GeneratedImage) => { if (!activeBrand) return; try { const updated = await bridge.unkeepImage(image.id, activeBrand); const restored = { ...image, path: updated.currentPath, prompt: updated.prompt ?? image.prompt, sourceTemplatePath: updated.sourceTemplatePath ?? image.sourceTemplatePath, timestamp: updated.timestamp || image.timestamp }; addToUnsorted([restored]); setCurrentBatch([restored, ...currentBatch]); setSelectedIndex(0); bumpStatusVersion(); toast.success('Image restored to unsorted') } catch (e) { console.error('Failed to undo keep:', e); toast.error('Failed to undo') } }, [activeBrand, addToUnsorted, bumpStatusVersion, currentBatch, setCurrentBatch, setSelectedIndex])

    const undoTrash = useCallback(async (image: GeneratedImage) => { if (!activeBrand) return; try { const updated = await bridge.restoreImage(image.id, activeBrand); const restored = { ...image, path: updated.currentPath, prompt: updated.prompt ?? image.prompt, sourceTemplatePath: updated.sourceTemplatePath ?? image.sourceTemplatePath, timestamp: updated.timestamp || image.timestamp }; addToUnsorted([restored]); setCurrentBatch([restored, ...currentBatch]); setSelectedIndex(0); bumpStatusVersion(); toast.success('Image restored to unsorted') } catch (e) { console.error('Failed to undo trash:', e); toast.error('Failed to undo') } }, [activeBrand, addToUnsorted, bumpStatusVersion, currentBatch, setCurrentBatch, setSelectedIndex])

    const handleKeep = useCallback(async () => { if (!currentImage || !activeBrand || currentImage.status === 'kept') return; const img = { ...currentImage }; try { await bridge.markImageKept(currentImage.id, activeBrand); removeFromUnsorted(currentImage.id); removeCurrentAndAdvance(); bumpStatusVersion(); if (lastToastId.current) toast.dismiss(lastToastId.current); lastToastId.current = toast('Image moved to Kept', { action: { label: 'Undo', onClick: () => undoKeep(img) } }) } catch (e) { console.error('Failed to mark image as kept:', e) } }, [currentImage, activeBrand, removeFromUnsorted, removeCurrentAndAdvance, bumpStatusVersion, undoKeep])

    const handleTrash = useCallback(async () => {
        if (!currentImage) { console.error('handleTrash: no currentImage'); return }
        if (!activeBrand) { console.error('handleTrash: no activeBrand'); return }
        const img = { ...currentImage }; try {
            if (currentImage.originalPath && currentImage.status === 'kept') {
                await bridge.trashByPath(currentImage.originalPath, activeBrand)
            } else { await bridge.markImageTrashed(currentImage.id, activeBrand) }
            removeFromUnsorted(currentImage.id); removeCurrentAndAdvance(); bumpStatusVersion(); if (lastToastId.current) toast.dismiss(lastToastId.current); lastToastId.current = toast('Image moved to Trash', { action: { label: 'Undo', onClick: () => undoTrash(img) } })
        } catch (e) { console.error('Failed to trash image:', e); toast.error('Failed to trash image') }
    }, [currentImage, activeBrand, removeFromUnsorted, removeCurrentAndAdvance, bumpStatusVersion, undoTrash])

    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return
            if (isTrashView || !hasImages) return
            if (e.key === 'g' || e.key === 'G') { e.preventDefault(); toggleBrowseMode(); return }
            if (isComparison || isGrid) return
            if ((e.key === 'k' || e.key === 'K') && !isKept) { e.preventDefault(); handleKeep() }
            else if (e.key === 't' || e.key === 'T') { e.preventDefault(); handleTrash() }
            else if (e.key === 'ArrowLeft' && selectedIndex > 0) { e.preventDefault(); setSelectedIndex(selectedIndex - 1) }
            else if (e.key === 'ArrowRight' && selectedIndex < currentBatch.length - 1) { e.preventDefault(); setSelectedIndex(selectedIndex + 1) }
        }
        window.addEventListener('keydown', handleKeyDown)
        return () => window.removeEventListener('keydown', handleKeyDown)
    }, [isTrashView, hasImages, isComparison, isGrid, isKept, handleKeep, handleTrash, selectedIndex, currentBatch.length, setSelectedIndex, toggleBrowseMode])

    if (isTrashView) return (<div className="flex-1 flex flex-col min-w-0 overflow-hidden bg-secondary/10"><TrashView onExit={handleExitTrash} /></div>)

    return (
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden bg-gradient-to-br from-gray-50 to-gray-200 dark:from-gray-900 dark:to-black relative">
            {hasImages ? (
                <>
                    {/* Main Workspace Area */}
                    <div className="relative flex-1 overflow-hidden p-12 pb-32 flex flex-col items-center justify-center">

                        {/* Top Info (Centered Title) */}
                        <div className="absolute top-8 left-1/2 -translate-x-1/2 z-20 animate-fade-in-up">
                            <h1 className="text-sm font-bold text-foreground/80 tracking-tight max-w-2xl truncate px-4" title={filename}>
                                {filename || 'Untitled'}
                            </h1>
                        </div>

                        {/* Center Content */}
                        <div className="w-full h-full flex items-center justify-center relative max-w-5xl mx-auto">
                            {isComparison ? (<ComparisonView />) : isGrid ? (<div className="w-full h-full overflow-y-auto pr-2"><ImageGrid /></div>) : (
                                <SwipeContainer onSwipeRight={handleKeep} onSwipeLeft={handleTrash} disabled={!currentImage || isKept} mode="curate">
                                    <div className="relative transition-all duration-300 transform">
                                        <ImageDisplay />
                                    </div>
                                </SwipeContainer>
                            )}
                        </div>

                        {/* Floating Action Toolbar - Centered above thumbnails */}
                        <div className="absolute bottom-24 left-1/2 -translate-x-1/2 z-30 animate-fade-in-up delay-100">
                            <div className="glass-pill px-2 py-1.5 flex items-center gap-1 shadow-float bg-white/80 dark:bg-zinc-900/80 backdrop-blur-2xl border-white/40 dark:border-white/10 ring-1 ring-black/5">
                                {!isKept && (
                                    <>
                                        <Tooltip>
                                            <TooltipTrigger asChild>
                                                <Button variant="ghost" size="icon" onClick={handleKeep} disabled={!currentImage} className="h-10 w-10 rounded-full hover:bg-emerald-500/10 hover:text-emerald-600 transition-all hover:scale-110">
                                                    <Heart className="w-5 h-5" fill="currentColor" fillOpacity={0.1} />
                                                </Button>
                                            </TooltipTrigger>
                                            <TooltipContent side="top">Keep (K)</TooltipContent>
                                        </Tooltip>

                                        <Tooltip>
                                            <TooltipTrigger asChild>
                                                <Button variant="ghost" size="icon" onClick={handleTrash} disabled={!currentImage} className="h-10 w-10 rounded-full hover:bg-red-500/10 hover:text-red-600 transition-all hover:scale-110">
                                                    <Trash2 className="w-5 h-5" />
                                                </Button>
                                            </TooltipTrigger>
                                            <TooltipContent side="top">Trash (T)</TooltipContent>
                                        </Tooltip>

                                        <div className="w-px h-6 bg-border mx-2" />
                                    </>
                                )}

                                <Tooltip>
                                    <TooltipTrigger asChild>
                                        <Button variant={isComparison ? 'secondary' : 'ghost'} size="icon" onClick={toggleComparison} className={cn("h-10 w-10 rounded-full transition-all hover:scale-105", isComparison && "bg-secondary text-foreground shadow-inner")}>
                                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" /></svg>
                                        </Button>
                                    </TooltipTrigger>
                                    <TooltipContent side="top">{isComparison ? 'Exit' : 'Compare'}</TooltipContent>
                                </Tooltip>

                                <Tooltip>
                                    <TooltipTrigger asChild>
                                        <Button variant={isGrid ? 'secondary' : 'ghost'} size="icon" onClick={toggleBrowseMode} className={cn("h-10 w-10 rounded-full transition-all hover:scale-105", isGrid && "bg-secondary text-foreground shadow-inner")}>
                                            {isGrid ? <ImageIcon className="w-5 h-5" /> : <LayoutGrid className="w-5 h-5" />}
                                        </Button>
                                    </TooltipTrigger>
                                    <TooltipContent side="top">{isGrid ? 'Preview' : 'Grid'}</TooltipContent>
                                </Tooltip>

                                <div className="w-px h-6 bg-border mx-2" />

                                <ExportActions />
                            </div>
                        </div>

                        {/* Context Panel (Info) - Absolute positioned to not take layout flow */}
                        {!isGrid && !isComparison && (
                            <div className="absolute right-8 top-1/2 -translate-y-1/2 z-10 opacity-0 hover:opacity-100 transition-opacity duration-300">
                                <div className="glass-panel p-4 rounded-2xl max-w-xs shadow-soft bg-white/60 dark:bg-black/40 backdrop-blur-xl border-white/20">
                                    <ContextPanel />
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Floating Thumbnails Dock */}
                    {!isGrid && (
                        <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-20 flex flex-col items-center gap-3">
                            {/* Relocated Counter */}
                            <div className="bg-black/5 dark:bg-white/5 backdrop-blur-md px-3 py-1 rounded-full border border-black/5 dark:border-white/5 animate-fade-in-up shadow-sm">
                                <span className="text-[10px] font-mono font-medium text-muted-foreground tracking-widest uppercase">
                                    {imageCounter}
                                </span>
                            </div>

                            <div className="glass-pill p-1.5 shadow-float bg-white/40 dark:bg-black/40 backdrop-blur-xl border-white/20 dark:border-white/5 ring-1 ring-white/20 max-w-[90vw]">
                                <ThumbnailStrip />
                            </div>
                        </div>
                    )}
                </>
            ) : (
                <EmptyState />
            )}
        </div>
    )
}
