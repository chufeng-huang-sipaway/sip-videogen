//Panel mode toggle for Creative Director vs Quick Create
import { Wand2, Zap } from 'lucide-react'
import { cn } from '@/lib/utils'
export type PanelMode = 'assistant' | 'playground'
interface PanelModeToggleProps { value: PanelMode; onChange: (m: PanelMode) => void; disabled?: boolean }
export function PanelModeToggle({ value, onChange, disabled }: PanelModeToggleProps) {
    const isPlayground = value === 'playground'
    return (
        <div className={cn("inline-flex items-center gap-1 p-1 rounded-full", disabled && "opacity-50 pointer-events-none")}>
            <button
                type="button"
                onClick={() => onChange('assistant')}
                className={cn(
                    "flex items-center gap-2 px-4 py-1.5 rounded-full text-sm font-medium transition-all duration-300",
                    !isPlayground
                        ? "bg-foreground text-background shadow-md backdrop-blur-sm scale-100"
                        : "text-muted-foreground hover:text-foreground hover:bg-muted/50 scale-95"
                )}
                disabled={disabled}
            >
                <Wand2 className="w-3.5 h-3.5" strokeWidth={2} />
                <span>Creative Director</span>
            </button>
            <button
                type="button"
                onClick={() => onChange('playground')}
                className={cn(
                    "flex items-center gap-2 px-4 py-1.5 rounded-full text-sm font-medium transition-all duration-300",
                    isPlayground
                        ? "bg-foreground text-background shadow-md backdrop-blur-sm scale-100"
                        : "text-muted-foreground hover:text-foreground hover:bg-muted/50 scale-95"
                )}
                disabled={disabled}
            >
                <Zap className="w-3.5 h-3.5 fill-current" strokeWidth={2} />
                <span>Quick Create</span>
            </button>
        </div>
    )
}
