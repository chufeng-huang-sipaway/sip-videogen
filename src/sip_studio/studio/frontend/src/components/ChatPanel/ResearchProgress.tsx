import { Button } from '@/components/ui/button'
import { Telescope } from 'lucide-react'
import type { PendingResearch } from '@/lib/bridge'
interface Props { research: PendingResearch & { status?: string; currentStage?: string }; onDismiss: () => void; onViewResults?: () => void }
export function ResearchProgress({ research, onDismiss, onViewResults }: Props) {
    const elapsed = Math.max(0, Math.floor((Date.now() - new Date(research.startedAt).getTime()) / 60000))
    const isComplete = research.status === 'completed'
    const isFailed = research.status === 'failed'
    return (
        <div className="rounded-2xl border border-white/20 bg-white/80 dark:bg-black/60 backdrop-blur-xl p-6 shadow-float w-full max-w-sm mx-auto animate-fade-in-up text-center relative overflow-hidden group">
            {/* Searchlight effect */}
            <div className="absolute inset-0 bg-gradient-to-tr from-transparent via-white/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none" />
            <div className="flex flex-col items-center justify-center space-y-4 relative z-10">
                <div className="relative">
                    <div className={`absolute inset-0 bg-brand-500/20 blur-xl rounded-full ${!isComplete && !isFailed ? 'animate-pulse' : ''}`} />
                    <Telescope className={`h-8 w-8 text-brand-500 relative z-10 ${!isComplete && !isFailed ? 'animate-bounce-subtle' : ''}`} style={{ animationDuration: '3s' }} />
                </div>
                <div className="space-y-1">
                    <h3 className="font-medium text-lg leading-tight">
                        {isComplete ? 'Research Complete' : isFailed ? 'Research Failed' : research.currentStage || 'Researching...'}
                    </h3>
                    <p className="text-sm text-muted-foreground line-clamp-1 max-w-[200px] mx-auto">{research.query}</p>
                </div>
                {!isComplete && !isFailed && (
                    <div className="text-xs text-muted-foreground font-medium">
                        <span>{elapsed}m elapsed</span>
                        <span className="mx-2">·</span>
                        <span>Typically 2-10 min</span>
                    </div>
                )}
                {isComplete && onViewResults && (
                    <Button size="sm" onClick={onViewResults} className="w-full bg-brand-500 hover:bg-brand-600 shadow-lg shadow-brand-500/20">View Results</Button>
                )}
                {isFailed && (
                    <Button variant="ghost" size="sm" onClick={onDismiss} className="text-destructive hover:text-destructive/80">Dismiss</Button>
                )}
            </div>
        </div>
    )
}
