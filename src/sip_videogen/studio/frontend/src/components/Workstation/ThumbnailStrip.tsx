//ThumbnailStrip component - horizontal thumbnail navigation for image batch with animations
import { useState, useEffect, useRef } from 'react'
import { useWorkstation } from '../../context/WorkstationContext'
import { bridge, isPyWebView } from '../../lib/bridge'
import { cn } from '../../lib/utils'
import { Loader2 } from 'lucide-react'
//Simple cache for thumbnails
const thumbCache = new Map<string, string>()
function Thumb({ path, isUnread }: { path: string; isUnread: boolean }) {
    const [src, setSrc] = useState<string | null>(() => thumbCache.get(path) ?? null)
    const [loading, setLoading] = useState(!thumbCache.has(path))
    const mountedRef = useRef(true)
    useEffect(() => { mountedRef.current = true; return () => { mountedRef.current = false } }, [])
    useEffect(() => {
        if (!path) { setLoading(false); return }
        if (thumbCache.has(path)) { setSrc(thumbCache.get(path)!); setLoading(false); return }
        if (path.startsWith('data:')) { setSrc(path); setLoading(false); return }
        if (!isPyWebView()) { setLoading(false); return }
        let cancelled = false
        async function load() {
            try {
                const dataUrl = await bridge.getAssetThumbnail(path)
                if (cancelled || !mountedRef.current) return
                thumbCache.set(path, dataUrl); setSrc(dataUrl)
            } catch (e) { console.error('Thumb load error:', e) } finally { if (!cancelled && mountedRef.current) setLoading(false) }
        }
        void load(); return () => { cancelled = true }
    }, [path])
    return (<div className="w-full h-full flex items-center justify-center bg-muted/20 relative">{loading ? (<Loader2 className="w-3 h-3 animate-spin text-muted-foreground/30" />) : src ? (<img src={src} alt="" className="w-full h-full object-cover" />) : null}{isUnread && <div className="absolute top-0.5 right-0.5 w-2.5 h-2.5 bg-blue-500 rounded-full border-2 border-background shadow-sm" />}</div>)
}
export function ThumbnailStrip() {
    const { currentBatch, selectedIndex, setSelectedIndex } = useWorkstation()
    const btnRefs = useRef<(HTMLButtonElement | null)[]>([])
    //Auto-center selected thumbnail (also triggers when batch changes to handle prepend)
    useEffect(() => { const btn = btnRefs.current[selectedIndex]; if (btn) btn.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' }) }, [selectedIndex, currentBatch.length, currentBatch[0]?.id])
    if (currentBatch.length <= 1) return null
    return (
        <div className="flex-shrink-0 w-full">
            <div className="flex gap-1.5 overflow-x-auto scrollbar-thin scrollbar-thumb-muted-foreground/20 scrollbar-track-transparent justify-center px-1 py-0.5">
                {currentBatch.map((img, i) => (
                    <button
                        key={img.id}
                        ref={el => { btnRefs.current[i] = el }}
                        onClick={() => setSelectedIndex(i)}
                        className={cn(
                            "flex-shrink-0 w-12 h-12 rounded-lg overflow-hidden border transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary/50 relative",
                            i === selectedIndex
                                ? "border-primary shadow-md ring-2 ring-primary/20 scale-105 z-10"
                                : "border-transparent opacity-70 hover:opacity-100 hover:scale-105"
                        )}
                    >
                        <Thumb path={img.originalPath || img.path || ''} isUnread={img.viewedAt === null} />
                    </button>
                ))}
            </div>
        </div>
    )
}
