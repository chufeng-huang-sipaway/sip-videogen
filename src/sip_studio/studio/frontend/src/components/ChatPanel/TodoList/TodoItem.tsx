//TodoItem component - displays single todo item with status and outputs
import { useState, useEffect } from 'react'
import { Check, Circle, Loader2, AlertCircle, PauseCircle, ImageIcon } from 'lucide-react'
import type { TodoItemData } from '@/lib/types/todo'
import { bridge, isPyWebView } from '@/lib/bridge'
import { cn } from '@/lib/utils'
interface TodoItemProps { item: TodoItemData }
//Strip file:// prefix from path
function normalizePath(p: string): string { return p.startsWith('file://') ? p.slice(7) : p }
export function TodoItem({ item }: TodoItemProps) {
  const isPending = item.status === 'pending'
  const isInProgress = item.status === 'in_progress'
  const isDone = item.status === 'done'
  const isError = item.status === 'error'
  const isPaused = item.status === 'paused'
  //Calculate placeholder count for in-progress items
  const outputCount = item.outputs?.length || 0
  const expectedCount = item.expectedOutputCount || 0
  const placeholderCount = isInProgress && expectedCount > outputCount ? expectedCount - outputCount : 0
  //Load images via bridge when outputs have paths but no data
  const [loadedUrls, setLoadedUrls] = useState<Map<number, string>>(new Map())
  useEffect(() => {
    if (!item.outputs) return
    const toLoad = item.outputs.map((o, i) => ({ idx: i, path: o.path, data: o.data })).filter(x => x.path && !x.data && !loadedUrls.has(x.idx))
    if (toLoad.length === 0) return
    let cancelled = false
    const load = async () => {
      for (const { idx, path } of toLoad) {
        if (cancelled) break
        const rawPath = normalizePath(path || '')
        if (!rawPath) continue
        try {
          let dataUrl: string | null = null
          if (isPyWebView()) dataUrl = await bridge.getImageData(rawPath)
          else dataUrl = rawPath.startsWith('/') ? `file://${rawPath}` : rawPath
          if (!cancelled && dataUrl) setLoadedUrls(prev => new Map(prev).set(idx, dataUrl!))
        } catch {/*ignore*/ }
      }
    }
    load()
    return () => { cancelled = true }
  }, [item.outputs, loadedUrls])
  return (
    <div
      className={cn(
        "group flex flex-col gap-2 rounded-xl border p-3 transition-all",
        isInProgress
          ? "border-brand-500/20 bg-brand-500/5 shadow-sm"
          : "border-transparent bg-muted/20 hover:bg-muted/30",
        isError && "border-destructive/20 bg-destructive/5",
        isPaused && "bg-muted/10 opacity-70"
      )}
    >
      {/* Header Row: Status + Description */}
      <div className="flex items-start gap-2">
        <div className="flex h-5 w-5 shrink-0 items-center justify-center pt-0.5">
          {isDone && (
            <div className="flex h-5 w-5 items-center justify-center rounded-full bg-success text-white shadow-sm">
              <Check className="h-3 w-3" strokeWidth={3} />
            </div>
          )}
          {isInProgress && <Loader2 className="h-4 w-4 animate-spin text-brand-500" />}
          {isPending && <Circle className="h-4 w-4 text-muted-foreground/30" strokeWidth={2} />}
          {isError && <AlertCircle className="h-4 w-4 text-destructive" strokeWidth={2} />}
          {isPaused && <PauseCircle className="h-4 w-4 text-muted-foreground" strokeWidth={2} />}
        </div>

        <span
          className={cn(
            "text-sm font-medium leading-tight transition-colors pt-0.5",
            isDone ? "text-muted-foreground" : "text-foreground",
            isInProgress && "text-brand-600 dark:text-brand-400"
          )}
        >
          {item.description}
        </span>
      </div>

      {/* Output Content Area */}
      {(outputCount > 0 || placeholderCount > 0) && (
        <div className="pl-7">
          <div className="flex flex-wrap gap-2">
            {item.outputs?.map((o, i) => {
              const imgSrc = o.data || loadedUrls.get(i)
              const isLoading = o.status === 'loading' || (!imgSrc && o.path)

              return (
                <div
                  key={i}
                  className={cn(
                    "relative h-12 w-12 overflow-hidden rounded-md border shadow-sm transition-all",
                    o.status === 'failed' || o.status === 'cancelled'
                      ? "border-destructive/30 bg-destructive/5"
                      : "border-border/40 bg-background",
                    imgSrc && "hover:scale-105 hover:shadow-md hover:ring-2 hover:ring-brand-500/20"
                  )}
                >
                  {isLoading ? (
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div className="absolute inset-0 -translate-x-full animate-[shimmer_2s_infinite] bg-gradient-to-r from-transparent via-muted/20 to-transparent" />
                      <ImageIcon strokeWidth={1.5} className="h-4 w-4 text-muted-foreground/30" />
                    </div>
                  ) : o.status === 'failed' ? (
                    <div className="flex h-full w-full flex-col items-center justify-center p-0.5 text-center">
                      <AlertCircle className="h-3 w-3 text-destructive/60" />
                    </div>
                  ) : o.status === 'cancelled' ? (
                    <div className="flex h-full w-full items-center justify-center">
                      <span className="text-[8px] text-muted-foreground/50">Cancelled</span>
                    </div>
                  ) : imgSrc ? (
                    <img
                      src={imgSrc}
                      className="h-full w-full object-cover animate-in fade-in duration-500"
                      alt={`Output ${i + 1}`}
                    />
                  ) : (
                    <div className="flex h-full w-full items-center justify-center">
                      <ImageIcon strokeWidth={1.5} className="h-4 w-4 text-muted-foreground/20" />
                    </div>
                  )}
                </div>
              )
            })}

            {/* Placeholders for expected outputs */}
            {Array.from({ length: placeholderCount }).map((_, i) => (
              <div
                key={`ph-${i}`}
                className="relative h-12 w-12 overflow-hidden rounded-md border border-dashed border-border/60 bg-muted/10"
              >
                <div className="absolute inset-0 -translate-x-full animate-[shimmer_3s_infinite] bg-gradient-to-r from-transparent via-white/5 to-transparent" />
              </div>
            ))}
          </div>
        </div>
      )}

      {item.error && (
        <div className="ml-7 rounded-md bg-destructive/10 p-2 text-xs font-medium text-destructive">
          {item.error}
        </div>
      )}
    </div>
  )
}
