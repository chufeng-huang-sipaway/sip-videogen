//ImageDisplay component - displays the currently selected image with smooth crossfade transitions
import { useState, useEffect, useRef, useCallback } from 'react'
import { useWorkstation } from '../../context/WorkstationContext'
import { useDrag } from '../../context/DragContext'
import { useQuickEdit } from '../../context/QuickEditContext'
import { useViewer } from '../../context/ViewerContext'
import { bridge, isPyWebView } from '../../lib/bridge'
import { Loader2, ChevronLeft, ChevronRight } from 'lucide-react'
import { QuickEditPreview, QuickEditResultImage } from './QuickEditPreview'
import { FullscreenControls } from './FullscreenControls'
import { InfoOverlay } from './InfoOverlay'
import { getFullCached, setFullCached, hasFullCached } from '../../lib/thumbnailCache'
import { cn } from '@/lib/utils'
const PRELOAD_RADIUS = 2
const WHEEL_SWIPE_THRESHOLD_PX = 80
const WHEEL_SWIPE_AXIS_LOCK_RATIO = 1.2
const WHEEL_GESTURE_IDLE_MS = 140
const DEBUG = false
function np(path: string): string { return path.startsWith('file://') ? path.slice('file://'.length) : path }
function dbg(...args: unknown[]) { if (DEBUG) console.log('[ImageDisplay]', ...args) }
function getWheelPhases(e: React.WheelEvent) { const ne = e.nativeEvent as unknown as { phase?: unknown; webkitPhase?: unknown; momentumPhase?: unknown; webkitMomentumPhase?: unknown }; const phase = typeof ne.phase === 'number' ? ne.phase : typeof ne.webkitPhase === 'number' ? ne.webkitPhase : undefined; const momentumPhase = typeof ne.momentumPhase === 'number' ? ne.momentumPhase : typeof ne.webkitMomentumPhase === 'number' ? ne.webkitMomentumPhase : undefined; return { phase, momentumPhase } }
const WHEEL_PHASE_BEGAN = 0x1
const WHEEL_PHASE_ENDED = 0x8
const WHEEL_PHASE_CANCELLED = 0x10
const WHEEL_PHASE_MAY_BEGIN = 0x20
type WheelGestureState = { active: boolean; handled: boolean; accX: number; accY: number; idleTimer: number | null }
function resetWheelGestureState(state: WheelGestureState) { state.active = false; state.handled = false; state.accX = 0; state.accY = 0; if (state.idleTimer !== null) { window.clearTimeout(state.idleTimer); state.idleTimer = null } }
function scheduleWheelGestureReset(state: WheelGestureState) { if (state.idleTimer !== null) window.clearTimeout(state.idleTimer); state.idleTimer = window.setTimeout(() => { state.active = false; state.handled = false; state.accX = 0; state.accY = 0; state.idleTimer = null }, WHEEL_GESTURE_IDLE_MS) }
export function ImageDisplay() {
    const { currentBatch, selectedIndex, updateImagePath, setSelectedIndex } = useWorkstation()
    const { setDragData, dragData } = useDrag()
    const { isGenerating, cancelEdit, resultPath } = useQuickEdit()
    const { zoom, panX, panY, isFullscreen, isPanning, naturalW, naturalH, containerW, containerH, setPan, setZoomAndPan, zoomToFit, zoomToActual, setNaturalSize, setContainerSize, setIsPanning, clampPan, resetView, clearDimensions } = useViewer()
    const currentImage = currentBatch[selectedIndex]
    const [isLoading, setIsLoading] = useState(false)
    const [slot0Src, setSlot0Src] = useState<string | null>(null)
    const [slot1Src, setSlot1Src] = useState<string | null>(null)
    const [activeSlot, setActiveSlot] = useState<0 | 1>(0)
    const [error, setError] = useState<string | null>(null)
    const [hovered, setHovered] = useState(false)
    const prevIdRef = useRef<string | null>(null)
    const wheelGestureRef = useRef<WheelGestureState>({ active: false, handled: false, accX: 0, accY: 0, idleTimer: null })
    const containerRef = useRef<HTMLDivElement>(null)
    const activeSlotRef = useRef<0 | 1>(activeSlot)
    const pendingSlotRef = useRef<0 | 1>(1)
    const pendingNonceRef = useRef(0)
    const zoomRef = useRef(zoom)
    const panRef = useRef({ x: panX, y: panY })
    const panStartRef = useRef({ x: 0, y: 0, panX: 0, panY: 0 })
    useEffect(() => { zoomRef.current = zoom }, [zoom])
    useEffect(() => { panRef.current = { x: panX, y: panY } }, [panX, panY])
    useEffect(() => { activeSlotRef.current = activeSlot }, [activeSlot])
    const canPrev = selectedIndex > 0, canNext = selectedIndex < currentBatch.length - 1
    const goPrev = useCallback(() => { if (canPrev && !isGenerating) setSelectedIndex(selectedIndex - 1) }, [canPrev, selectedIndex, setSelectedIndex, isGenerating])
    const goNext = useCallback(() => { if (canNext && !isGenerating) setSelectedIndex(selectedIndex + 1) }, [canNext, selectedIndex, setSelectedIndex, isGenerating])
    //Cursor-centered zoom handler - uses atomic setZoomAndPan to prevent race condition
    const handleZoom = useCallback((e: WheelEvent) => { const z = zoomRef.current, p = panRef.current, factor = e.deltaY > 0 ? 0.9 : 1.1, newZoom = Math.max(1, Math.min(5, z * factor)); if (newZoom === z) return; const rect = containerRef.current!.getBoundingClientRect(), cx = e.clientX - rect.left - rect.width / 2, cy = e.clientY - rect.top - rect.height / 2, newPanX = p.x + cx * (1 / newZoom - 1 / z), newPanY = p.y + cy * (1 / newZoom - 1 / z); setZoomAndPan(newZoom, newPanX, newPanY) }, [setZoomAndPan])
    //Double-click: toggle between fit and actual size
    const handleDoubleClick = useCallback(() => { if (zoom <= 1.01) zoomToActual(); else zoomToFit() }, [zoom, zoomToActual, zoomToFit])
    //Pointer pan handlers
    const handlePointerDown = (e: React.PointerEvent) => { if (e.button !== 0 || zoomRef.current <= 1.01) return; e.currentTarget.setPointerCapture(e.pointerId); setIsPanning(true); panStartRef.current = { x: e.clientX, y: e.clientY, panX: panRef.current.x, panY: panRef.current.y } }
    const handlePointerMove = (e: React.PointerEvent) => { if (!isPanning) return; const z = zoomRef.current, dx = (e.clientX - panStartRef.current.x) / z, dy = (e.clientY - panStartRef.current.y) / z; setPan(panStartRef.current.panX + dx, panStartRef.current.panY + dy) }
    const handlePointerUp = (e: React.PointerEvent) => { if (e.currentTarget.hasPointerCapture(e.pointerId)) e.currentTarget.releasePointerCapture(e.pointerId); setIsPanning(false); clampPan() }
    const handlePointerCancel = handlePointerUp
    //Image load/error handlers for natural size
    const handleImgLoad = (e: React.SyntheticEvent<HTMLImageElement>) => { const img = e.currentTarget; setNaturalSize(img.naturalWidth, img.naturalHeight) }
    const handleImgError = () => { clearDimensions() }
    //Reset view on image change
    useEffect(() => { if (currentImage?.id !== prevIdRef.current) { resetView() } }, [currentImage?.id, resetView])
    //ResizeObserver for container size
    useEffect(() => { const el = containerRef.current; if (!el || typeof ResizeObserver === 'undefined') return; const ro = new ResizeObserver((entries) => { const { width, height } = entries[0].contentRect; setContainerSize(width, height); clampPan() }); ro.observe(el); return () => ro.disconnect() }, [setContainerSize, clampPan])
    //Wheel handler: zoom (Cmd/Ctrl) or pan when zoomed, else swipe navigation
    useEffect(() => { const el = containerRef.current; if (!el) return; const handler = (e: WheelEvent) => { const z = zoomRef.current; if (e.ctrlKey || e.metaKey) { e.preventDefault(); e.stopPropagation(); handleZoom(e); return } if (z > 1.01) { e.preventDefault(); e.stopPropagation(); const p = panRef.current, newPanX = p.x - e.deltaX / z, newPanY = p.y - e.deltaY / z; setZoomAndPan(z, newPanX, newPanY); return } }; el.addEventListener('wheel', handler, { passive: false }); return () => el.removeEventListener('wheel', handler) }, [handleZoom, setZoomAndPan])
    //Trackpad swipe handler - exactly one image per wheel/scroll gesture
    const handleWheel = useCallback((e: React.WheelEvent) => {
        if (isGenerating) return //Disable swipe during generation
        const dx = e.deltaX, dy = e.deltaY
        const state = wheelGestureRef.current
        const { phase, momentumPhase } = getWheelPhases(e)
        //Prefer WebKit gesture phases (PyWebView on macOS) for reliable "one nav per gesture"
        if (typeof phase === 'number' || typeof momentumPhase === 'number') {
            const p = phase ?? 0
            const mp = momentumPhase ?? 0
            const started = (p & (WHEEL_PHASE_BEGAN | WHEEL_PHASE_MAY_BEGIN)) !== 0
            const ended = (p & (WHEEL_PHASE_ENDED | WHEEL_PHASE_CANCELLED)) !== 0
            //Ignore momentum wheel events (finger lifted) so they can't trigger extra nav or keep the gesture "stuck"
            if (mp !== 0) { resetWheelGestureState(state); return }
            if (started) { state.active = true; state.handled = false; state.accX = 0; state.accY = 0 }
            if (!state.active) { state.active = true; state.handled = false; state.accX = 0; state.accY = 0 }
            scheduleWheelGestureReset(state)
            state.accX += dx; state.accY += dy
            if (!state.handled) {
                const absX = Math.abs(state.accX), absY = Math.abs(state.accY)
                if (absX >= WHEEL_SWIPE_THRESHOLD_PX && absX > absY * WHEEL_SWIPE_AXIS_LOCK_RATIO) {
                    state.handled = true
                    if (state.accX > 0 && canNext) setSelectedIndex(selectedIndex + 1)
                    else if (state.accX < 0 && canPrev) setSelectedIndex(selectedIndex - 1)
                }
            }
            if (ended) resetWheelGestureState(state)
            return
        }
        //Fallback heuristic: treat a burst of wheel events as one gesture (idle gap ends gesture)
        if (!state.active) { state.active = true; state.handled = false; state.accX = 0; state.accY = 0 }
        state.accX += dx; state.accY += dy
        scheduleWheelGestureReset(state)
        if (state.handled) return
        const absX = Math.abs(state.accX), absY = Math.abs(state.accY)
        if (absX < WHEEL_SWIPE_THRESHOLD_PX || absX <= absY * WHEEL_SWIPE_AXIS_LOCK_RATIO) return
        state.handled = true
        if (state.accX > 0 && canNext) setSelectedIndex(selectedIndex + 1)
        else if (state.accX < 0 && canPrev) setSelectedIndex(selectedIndex - 1)
    }, [canPrev, canNext, selectedIndex, setSelectedIndex, isGenerating])
    const activeSrc = activeSlot === 0 ? slot0Src : slot1Src
    dbg('render', { id: currentImage?.id, selectedIndex, batchLen: currentBatch.length, isLoading, activeSlot, hasActive: !!activeSrc, slot0: !!slot0Src, slot1: !!slot1Src, error })
    //Handle image transition - keep current visible, load next into the hidden slot
    useEffect(() => {
        if (!currentImage) return
        if (prevIdRef.current !== currentImage.id) {
            dbg('id changed', prevIdRef.current, '→', currentImage.id)
            pendingNonceRef.current += 1
            const nextSlot: 0 | 1 = activeSlotRef.current === 0 ? 1 : 0
            pendingSlotRef.current = nextSlot
            if (nextSlot === 0) setSlot0Src(null)
            else setSlot1Src(null)
            setIsLoading(true)
            setError(null)
            prevIdRef.current = currentImage.id
        }
    }, [currentImage?.id])
    //Resolve image source (prefer data URLs; otherwise load via bridge)
    useEffect(() => {
        let cancelled = false
        async function load() {
            if (!currentImage) { dbg('no currentImage'); return }
            const raw = currentImage.path
            const origPath = currentImage.originalPath
            dbg('load start', { raw: raw?.slice(-40), origPath: origPath?.slice(-40) })
            //Check shared cache first - if cached, swap instantly
            const cacheKey = origPath || np(raw || '')
            const targetSlot = pendingSlotRef.current
            if (cacheKey && hasFullCached(cacheKey)) {
                const cached = getFullCached(cacheKey)!
                dbg('cache hit', cacheKey.slice(-40))
                if (targetSlot === 0) setSlot0Src(cached)
                else setSlot1Src(cached)
                return
            }
            dbg('cache miss', cacheKey?.slice(-40))
            //Lazy loading: if path is empty but originalPath exists, load via getAssetFull
            if ((!raw || raw === '') && origPath) {
                dbg('using getAssetFull branch')
                if (!isPyWebView()) { setIsLoading(false); setError('Cannot load in browser'); return }
                try {
                    const dataUrl = await bridge.getAssetFull(origPath)
                    dbg('getAssetFull result', { len: dataUrl?.length, cancelled })
                    if (cancelled) return
                    if (dataUrl && dataUrl !== '') {
                        setFullCached(origPath, dataUrl); updateImagePath(currentImage.id, dataUrl)
                        if (targetSlot === 0) setSlot0Src(dataUrl)
                        else setSlot1Src(dataUrl)
                    }
                    else { setIsLoading(false); setError('Image not found') }
                } catch (e) { dbg('getAssetFull error', e); if (!cancelled) { setError(e instanceof Error ? e.message : String(e)); setIsLoading(false) } }
                return
            }
            if (!raw || raw === '') { dbg('missing path'); setIsLoading(false); setError('Missing image path'); return }
            if (raw.startsWith('data:') || raw.startsWith('http://') || raw.startsWith('https://')) {
                dbg('direct URL')
                if (targetSlot === 0) setSlot0Src(raw)
                else setSlot1Src(raw)
                return
            }
            const normalized = np(raw)
            dbg('using getImageData branch', normalized.slice(-40))
            if (!isPyWebView()) {
                const url = normalized.startsWith('/') ? `file://${normalized}` : normalized
                if (targetSlot === 0) setSlot0Src(url)
                else setSlot1Src(url)
                return
            }
            try {
                const dataUrl = await bridge.getImageData(normalized)
                dbg('getImageData result', { len: dataUrl?.length, cancelled })
                if (cancelled) return
                if (dataUrl && dataUrl !== '') {
                    setFullCached(normalized, dataUrl)
                    if (targetSlot === 0) setSlot0Src(dataUrl)
                    else setSlot1Src(dataUrl)
                    dbg('slot src set', { slot: targetSlot })
                }
                else { setIsLoading(false); setError('Image not found') }
            } catch (e) { dbg('getImageData error', e); if (!cancelled) { setError(e instanceof Error ? e.message : String(e)); setIsLoading(false) } }
        }
        void load()
        return () => { dbg('cleanup - setting cancelled'); cancelled = true }
    }, [currentImage?.id, currentImage?.path, currentImage?.originalPath, updateImagePath])
    //Preload adjacent images after current loads
    useEffect(() => {
        if (!currentImage || !isPyWebView() || isLoading) return
        let cancelled = false
        async function preload() {
            for (let offset = -PRELOAD_RADIUS; offset <= PRELOAD_RADIUS; offset++) {
                if (offset === 0 || cancelled) continue
                const idx = selectedIndex + offset
                if (idx < 0 || idx >= currentBatch.length) continue
                const img = currentBatch[idx]
                const path = img.originalPath || img.path
                if (!path || path.startsWith('data:')) continue
                const key = img.originalPath || np(path)
                if (hasFullCached(key)) continue
                try {
                    const dataUrl = img.originalPath ? await bridge.getAssetFull(img.originalPath) : await bridge.getImageData(np(path))
                    if (!cancelled) setFullCached(key, dataUrl)
                } catch { }
            }
        }
        void preload()
        return () => { cancelled = true }
    }, [selectedIndex, currentBatch, currentImage, isLoading])
    const commitLoadedSlot = useCallback((slot: 0 | 1, img: HTMLImageElement, nonce: number) => {
        requestAnimationFrame(() => {
            if (pendingNonceRef.current !== nonce) return
            if (pendingSlotRef.current !== slot) return
            setNaturalSize(img.naturalWidth, img.naturalHeight)
            setActiveSlot(slot)
            if (slot === 0) setSlot1Src(null)
            else setSlot0Src(null)
            setIsLoading(false)
        })
    }, [setNaturalSize])
    const handleSlotLoad = useCallback((slot: 0 | 1, expectedSrc: string | null) => (e: React.SyntheticEvent<HTMLImageElement>) => {
        if (!expectedSrc) return
        if (e.currentTarget.getAttribute('src') !== expectedSrc) return
        const nonce = pendingNonceRef.current
        if (pendingSlotRef.current === slot) commitLoadedSlot(slot, e.currentTarget, nonce)
        else if (activeSlotRef.current === slot) handleImgLoad(e)
    }, [commitLoadedSlot])
    const handleSlotError = useCallback((slot: 0 | 1) => () => {
        if (pendingSlotRef.current === slot) { setIsLoading(false); setError('Failed to load image') }
        if (activeSlotRef.current === slot) handleImgError()
    }, [handleImgError])
    //Use mousedown to initiate drag (bypasses PyWebView/WebKit HTML5 drag issues)
    const handleMouseDown = (e: React.MouseEvent) => { if (e.button !== 0 || isGenerating) return; const path = currentImage?.originalPath || currentImage?.path; if (!path || path.startsWith('data:')) return; setDragData({ type: 'asset', path, thumbnailUrl: activeSrc || undefined }) }
    if (!currentImage) return null
    const debugInfo = DEBUG ? `id:${currentImage.id?.slice(-8) || '?'} idx:${selectedIndex} slot:${activeSlot} loading:${isLoading} err:${error || 'none'}` : ''
    const isDragging = !!dragData
    const imgClass = cn("absolute inset-0 w-full h-full object-contain select-none", isDragging && "opacity-50")
    const navBtnClass = "absolute top-1/2 -translate-y-1/2 z-20 p-2 rounded-full bg-black/50 text-white/90 backdrop-blur-sm transition-all hover:bg-black/70 hover:scale-110 disabled:opacity-30 disabled:pointer-events-none"
    const cursor = zoom > 1.01 ? (isPanning ? 'grabbing' : 'grab') : 'grab'
    const stageStyle: React.CSSProperties = { transform: `scale(${zoom}) translate(${panX}px, ${panY}px)`, transformOrigin: 'center center', willChange: 'transform' }
    if (naturalW && naturalH && containerW > 0 && containerH > 0) {
        const fitScale = Math.min(containerW / naturalW, containerH / naturalH, 1)
        stageStyle.width = Math.round(naturalW * fitScale)
        stageStyle.height = Math.round(naturalH * fitScale)
    } else {
        stageStyle.width = '100%'
        stageStyle.height = '100%'
    }
    return (<div ref={containerRef} style={{ cursor }} className={cn("w-full h-full flex items-center justify-center relative", isFullscreen && "fixed inset-0 z-50 bg-black")} onMouseEnter={() => setHovered(true)} onMouseLeave={() => setHovered(false)} onWheel={handleWheel} onDoubleClick={handleDoubleClick} onPointerDown={handlePointerDown} onPointerMove={handlePointerMove} onPointerUp={handlePointerUp} onPointerCancel={handlePointerCancel}>
        {DEBUG && (<div className="absolute top-2 left-2 right-2 z-50 bg-black/80 text-white text-[10px] font-mono p-2 rounded">{debugInfo}</div>)}
        {/* Outer wrapper - absolute positioning for reliable height calculation */}
        <div className="absolute inset-0 flex items-center justify-center">
            {/* Image container - relative for overlays */}
            <div className="relative flex items-center justify-center" style={stageStyle}>
                {/* Stable shadow plate (avoids WebKit drop-shadow clipping + eliminates flicker) */}
                {naturalW && naturalH && !error && (
                    <div
                        className="absolute inset-0 pointer-events-none"
                        style={{ boxShadow: '0 20px 50px rgba(0,0,0,0.15)' }}
                    />
                )}
                {/* Double-buffered images: keep current visible until next fully loaded, then swap instantly */}
                {slot0Src && !error && (
                    <img
                        draggable={false}
                        onMouseDown={activeSlot === 0 ? handleMouseDown : undefined}
                        onLoad={handleSlotLoad(0, slot0Src)}
                        onError={handleSlotError(0)}
                        src={slot0Src}
                        alt=""
                        className={imgClass}
                        style={{ opacity: activeSlot === 0 ? 1 : 0, pointerEvents: activeSlot === 0 ? 'auto' : 'none' }}
                    />
                )}
                {slot1Src && !error && (
                    <img
                        draggable={false}
                        onMouseDown={activeSlot === 1 ? handleMouseDown : undefined}
                        onLoad={handleSlotLoad(1, slot1Src)}
                        onError={handleSlotError(1)}
                        src={slot1Src}
                        alt={currentImage.prompt || 'Generated image'}
                        className={imgClass}
                        style={{ opacity: activeSlot === 1 ? 1 : 0, pointerEvents: activeSlot === 1 ? 'auto' : 'none' }}
                    />
                )}
                {/* Quick Edit result image - inside wrapper to match original image bounds */}
                {resultPath && !isGenerating && <QuickEditResultImage />}
                {/* Shimmer overlay with sparkles - now contained to image area */}
                {isGenerating && (<><div className="shimmer-overlay rounded-lg" /><div className="shimmer-sparkles rounded-lg">{Array.from({ length: 38 }, (_, i) => <span key={i} className={`sparkle${i % 3 === 1 ? ' brand' : ''}`} />)}</div><button onClick={cancelEdit} className="magic-stop-btn" style={{ pointerEvents: 'auto' }}><span className="magic-stop-icon" /></button></>)}
            </div>
        </div>
        {/* Loading indicator */}
        {isLoading && !activeSrc && (<div className="absolute inset-0 flex items-center justify-center"><Loader2 className="w-8 h-8 animate-spin text-muted-foreground/30" /></div>)}
        {/* Error state */}
        {!isLoading && error && !activeSrc && (<div className="text-sm text-muted-foreground">{error}</div>)}
        {/* Quick Edit result preview - outside wrappers to prevent clipping */}
        {resultPath && !isGenerating && <QuickEditPreview />}
        {/* Navigation buttons - hidden in fullscreen since FullscreenControls handles it */}
        {!isFullscreen && <><button onClick={goPrev} disabled={!canPrev || isGenerating} className={cn(navBtnClass, "left-6 w-12 h-12 flex items-center justify-center bg-white/40 dark:bg-black/40 backdrop-blur-md hover:bg-white/60 dark:hover:bg-black/60 shadow-lg text-foreground hover:scale-105 transition-all duration-300 rounded-full", hovered && !isGenerating ? "opacity-100" : "opacity-0")}><ChevronLeft className="w-6 h-6" strokeWidth={1.5} /></button>
            <button onClick={goNext} disabled={!canNext || isGenerating} className={cn(navBtnClass, "right-6 w-12 h-12 flex items-center justify-center bg-white/40 dark:bg-black/40 backdrop-blur-md hover:bg-white/60 dark:hover:bg-black/60 shadow-lg text-foreground hover:scale-105 transition-all duration-300 rounded-full", hovered && !isGenerating ? "opacity-100" : "opacity-0")}><ChevronRight className="w-6 h-6" strokeWidth={1.5} /></button></>}
        {/* Info overlay */}
        <InfoOverlay />
        {/* Fullscreen controls overlay */}
        {isFullscreen && <FullscreenControls />}
    </div>)
}
