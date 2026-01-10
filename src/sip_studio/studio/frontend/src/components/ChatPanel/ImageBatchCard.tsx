//ImageBatchCard - shows loading/completed/failed states for batch image generation
import { useState, useEffect } from 'react'
import { Check, ImageIcon, AlertCircle } from 'lucide-react'
import { Spinner } from '@/components/ui/spinner'
import { bridge, isPyWebView } from '@/lib/bridge'
import type { ImageProgressEvent } from '@/lib/bridge'
import { cn } from '@/lib/utils'

interface Props {
    tickets: Map<string, ImageProgressEvent>
    expectedCount: number
}

// Strip file:// prefix from path
function normalizePath(p: string): string {
    return p.startsWith('file://') ? p.slice(7) : p
}

export function ImageBatchCard({ tickets, expectedCount }: Props) {
    const [loadedUrls, setLoadedUrls] = useState<Map<string, string>>(new Map())

    // Load images via bridge.getImageData when completed tickets have paths
    useEffect(() => {
        const toLoad = Array.from(tickets.values()).filter(t =>
            t.status === 'completed' && (t.rawPath || t.path) && !loadedUrls.has(t.ticketId)
        )

        if (toLoad.length === 0) return

        let cancelled = false
        const loadImages = async () => {
            for (const ticket of toLoad) {
                if (cancelled) break
                const rawPath = ticket.rawPath || normalizePath(ticket.path || '')
                if (!rawPath) continue

                try {
                    let dataUrl: string | null = null
                    if (isPyWebView()) {
                        dataUrl = await bridge.getImageData(rawPath)
                    } else {
                        dataUrl = rawPath.startsWith('/') ? `file://${rawPath}` : rawPath
                    }

                    if (!cancelled && dataUrl) {
                        setLoadedUrls(prev => new Map(prev).set(ticket.ticketId, dataUrl!))
                    }
                } catch {
                    /* ignore load errors */
                }
            }
        }
        loadImages()
        return () => { cancelled = true }
    }, [tickets, loadedUrls])

    if (tickets.size === 0 && expectedCount === 0) return null

    const items = Array.from(tickets.values())
    const completed = items.filter(t => t.status === 'completed').length
    const failed = items.filter(t => t.status === 'failed').length
    const total = Math.max(items.length, expectedCount)
    const allDone = items.length >= expectedCount && items.every(t =>
        t.status === 'completed' || t.status === 'failed' || t.status === 'cancelled' || t.status === 'timeout'
    )

    // Build slots - use tickets we have plus placeholders for expected count
    const slots: Array<ImageProgressEvent | null> = []
    for (let i = 0; i < total; i++) {
        slots.push(items[i] || null)
    }

    return (
        <div className={cn(
            "overflow-hidden rounded-2xl border border-white/20 shadow-xl transition-all",
            "bg-background/80 backdrop-blur-md"
        )}>
            {/* Header */}
            <div className="flex items-center gap-3 border-b border-white/10 p-4">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-muted/20 ring-1 ring-inset ring-white/10">
                    {!allDone ? (
                        <Spinner className="h-4 w-4 text-brand-500" />
                    ) : (
                        <Check strokeWidth={2} className="h-4 w-4 text-success" />
                    )}
                </div>

                <div className="flex flex-col gap-0.5">
                    <span className="font-semibold tracking-tight text-foreground">
                        {!allDone ? `Generating ${total} image${total > 1 ? 's' : ''}...` :
                            failed > 0 ? `Generated ${completed}/${total} images` :
                                `Generated ${total} image${total > 1 ? 's' : ''}`
                        }
                    </span>
                    {!allDone && completed > 0 && (
                        <span className="text-xs text-muted-foreground">
                            {completed} completed, {total - completed} remaining
                        </span>
                    )}
                </div>
            </div>

            {/* Image grid */}
            <div className={cn(
                "grid gap-3 p-4",
                total === 1 ? 'grid-cols-1' : total <= 4 ? 'grid-cols-2' : 'grid-cols-3'
            )}>
                {slots.map((ticket, i) => {
                    const dataUrl = ticket ? loadedUrls.get(ticket.ticketId) : undefined
                    const isCompleted = ticket?.status === 'completed'
                    const hasPath = !!(ticket?.rawPath || ticket?.path)
                    const isFailed = ticket?.status === 'failed'
                    const isCancelled = ticket?.status === 'cancelled' || ticket?.status === 'timeout'

                    return (
                        <div
                            key={ticket?.ticketId || `slot-${i}`}
                            className={cn(
                                "relative aspect-square overflow-hidden rounded-lg border transition-all",
                                isCompleted ? "border-white/10 shadow-sm hover:scale-[1.02] hover:shadow-md" : "border-white/5 bg-muted/10"
                            )}
                        >
                            {isCompleted && dataUrl ? (
                                <img
                                    src={dataUrl}
                                    className="h-full w-full object-cover animate-in fade-in duration-500"
                                    alt=""
                                    loading="lazy"
                                />
                            ) : isCompleted && hasPath ? (
                                // Completed but loading local URL
                                <div className="absolute inset-0 flex items-center justify-center bg-muted/20">
                                    <div className="absolute inset-0 -translate-x-full animate-[shimmer_1.5s_infinite] bg-gradient-to-r from-transparent via-white/10 to-transparent" />
                                    <ImageIcon strokeWidth={1.5} className="h-6 w-6 text-muted-foreground/30" />
                                </div>
                            ) : isFailed ? (
                                <div className="flex h-full w-full flex-col items-center justify-center bg-destructive/5 p-2 text-center text-destructive">
                                    <AlertCircle className="mb-1 h-5 w-5 opacity-50" />
                                    <span className="line-clamp-2 text-[10px] font-medium opacity-90">{ticket?.error || 'Failed'}</span>
                                </div>
                            ) : isCancelled ? (
                                <div className="flex h-full w-full items-center justify-center bg-muted/30">
                                    <span className="text-xs text-muted-foreground/60">
                                        {ticket?.status === 'timeout' ? 'Timeout' : 'Cancelled'}
                                    </span>
                                </div>
                            ) : (
                                // Loading / Waiting State
                                <div className="absolute inset-0 flex items-center justify-center">
                                    <div className="absolute inset-0 -translate-x-full animate-[shimmer_2s_infinite] bg-gradient-to-r from-transparent via-white/5 to-transparent" />
                                    <ImageIcon strokeWidth={1} className="h-6 w-6 text-muted-foreground/20" />
                                </div>
                            )}
                        </div>
                    )
                })}
            </div>
        </div>
    )
}
