//ImageDisplay component - displays the currently selected image with transitions
import { useState, useEffect, useRef } from 'react'
import { useWorkstation } from '../../context/WorkstationContext'
import { bridge, isPyWebView } from '../../lib/bridge'
import { Loader2 } from 'lucide-react'
const fullImageCache = new Map<string, string>()
function normalizeImagePath(path: string): string {
    return path.startsWith('file://') ? path.slice('file://'.length) : path
}
export function ImageDisplay() {
    const { currentBatch, selectedIndex, updateImagePath } = useWorkstation()
    const currentImage = currentBatch[selectedIndex]
    const [isLoading, setIsLoading] = useState(true)
    const [isVisible, setIsVisible] = useState(false)
    const [src, setSrc] = useState<string | null>(null)
    const [error, setError] = useState<string | null>(null)
    const prevIdRef = useRef<string | null>(null)
    //Handle image transition on selection change
    useEffect(() => { if (!currentImage) return; if (prevIdRef.current !== currentImage.id) { setIsVisible(false); setIsLoading(true); setSrc(null); setError(null); const t = setTimeout(() => setIsVisible(true), 50); prevIdRef.current = currentImage.id; return () => clearTimeout(t) } },
        [currentImage])
    //Resolve image source (prefer data URLs; otherwise load via bridge to avoid file:// restrictions)
    useEffect(() => {
        let cancelled = false
        async function load() {
            if (!currentImage) return
            const raw = currentImage.path
            const origPath = currentImage.originalPath
            //Lazy loading: if path is empty but originalPath exists, load via getAssetFull
            if ((!raw || raw === '') && origPath) {
                if (!isPyWebView()) { setIsLoading(false); setError('Cannot load in browser'); return }
                try {
                    const dataUrl = await bridge.getAssetFull(origPath)
                    if (cancelled) return
                    if (!dataUrl || dataUrl === '') { setIsLoading(false); setError('Failed to load image data'); return }
                    updateImagePath(currentImage.id, dataUrl)
                    setSrc(dataUrl)
                } catch (e) {
                    if (cancelled) return
                    setError(e instanceof Error ? e.message : String(e))
                    setIsLoading(false)
                }
                return
            }
            if (!raw || raw === '') { setIsLoading(false); setError('Missing image path'); return }
            if (raw.startsWith('data:') || raw.startsWith('http://') || raw.startsWith('https://')) { setSrc(raw); return }
            const normalized = normalizeImagePath(raw)
            if (fullImageCache.has(normalized)) { setSrc(fullImageCache.get(normalized)!); return }
            if (!isPyWebView()) {
                setSrc(normalized.startsWith('/') ? `file://${normalized}` : normalized)
                return
            }
            try {
                const dataUrl = await bridge.getImageData(normalized)
                if (cancelled) return
                fullImageCache.set(normalized, dataUrl)
                setSrc(dataUrl)
            } catch (e) {
                if (cancelled) return
                setError(e instanceof Error ? e.message : String(e))
                setIsLoading(false)
            }
        }
        void load()
        return () => { cancelled = true }
    }, [currentImage?.id, currentImage?.path, currentImage?.originalPath, updateImagePath])
    const handleLoad = () => { setIsLoading(false) }
    const handleError = () => { setIsLoading(false); setError('Failed to load image') }
    if (!currentImage) return null
    return (<div className="w-full h-full flex items-center justify-center relative">{isLoading && (<div className="absolute inset-0 flex items-center justify-center z-10"><Loader2 className="w-8 h-8 animate-spin text-muted-foreground/50" /></div>)}{!isLoading && error && (<div className="text-sm text-muted-foreground">{error}</div>)}{src && (<img src={src} alt={currentImage.prompt || 'Generated image'} onLoad={handleLoad} onError={handleError} className={`max-w-full max-h-full object-contain rounded-2xl shadow-2xl ring-1 ring-black/5 dark:ring-white/10 transition-all duration-500 ease-out ${isVisible && !isLoading && !error ? 'opacity-100 scale-100' : 'opacity-0 scale-98'}`} />)}{!src && !isLoading && !error && (<div className="text-sm text-muted-foreground">Image unavailable</div>)}</div>)
}
