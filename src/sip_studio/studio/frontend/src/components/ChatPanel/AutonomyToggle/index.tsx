//AutonomyToggle - Segmented control for review-first vs auto modes
import { Bot, Eye } from 'lucide-react'
import { cn } from '@/lib/utils'
interface AutonomyToggleProps { enabled: boolean; onChange: (enabled: boolean) => void; disabled?: boolean }
export function AutonomyToggle({ enabled, onChange, disabled }: AutonomyToggleProps) {
    return (<div className={cn("inline-flex items-center h-8 rounded-full bg-white/50 dark:bg-white/10 border border-border/40 p-0.5", disabled && "opacity-50 pointer-events-none")}>
        <button type="button" onClick={() => onChange(false)} disabled={disabled} className={cn("flex items-center gap-1.5 h-full px-2.5 rounded-full text-xs font-medium transition-all", !enabled ? "bg-background shadow-sm text-foreground" : "text-muted-foreground hover:text-foreground")}>
            <Eye className="h-3.5 w-3.5" />
            <span>Review</span>
        </button>
        <button type="button" onClick={() => onChange(true)} disabled={disabled} className={cn("flex items-center gap-1.5 h-full px-2.5 rounded-full text-xs font-medium transition-all", enabled ? "bg-background shadow-sm text-foreground" : "text-muted-foreground hover:text-foreground")}>
            <Bot className="h-3.5 w-3.5" />
            <span>Auto</span>
        </button>
    </div>)
}
