//QuickEditButton - AI-powered image edit with popover input
import { useState, useCallback, useRef, useEffect } from 'react'
import { useWorkstation } from '../../context/WorkstationContext'
import { useQuickEdit } from '../../context/QuickEditContext'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { Popover, PopoverTrigger, PopoverContent } from '../ui/popover'
import { Tooltip, TooltipContent, TooltipTrigger } from '../ui/tooltip'
import { Wand2, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
const MAX_LEN = 500
interface QuickEditButtonProps { variant?: 'light' | 'dark' }
export function QuickEditButton({ }: QuickEditButtonProps) {
    const { currentBatch, selectedIndex } = useWorkstation()
    const { isGenerating, submitEdit, error: ctxError, clearError, prompt: ctxPrompt, resultPath } = useQuickEdit()
    const curr = currentBatch[selectedIndex]
    const imgPath = curr?.originalPath || curr?.path || ''
    const hasImg = !!imgPath
    const [open, setOpen] = useState(false)
    const [prompt, setPrompt] = useState('')
    const [err, setErr] = useState('')
    const inputRef = useRef<HTMLInputElement>(null)
    const btnCls = cn("h-9 w-9 rounded-full transition-all", "text-white/90")
    //Auto-open when rerun is triggered (resultPath cleared, ctxPrompt set)
    useEffect(() => { if (!resultPath && ctxPrompt && !open) { setPrompt(ctxPrompt); setOpen(true) } }, [resultPath, ctxPrompt, open])
    //Focus input on open
    useEffect(() => { if (open) setTimeout(() => inputRef.current?.focus(), 50) }, [open])
    //Reset on close (only if no rerun pending)
    useEffect(() => { if (!open && !ctxPrompt) { setPrompt(''); setErr(''); clearError() } }, [open, clearError, ctxPrompt])
    //Show context error
    useEffect(() => { if (ctxError) setErr(ctxError) }, [ctxError])
    //Validate & submit
    const handleSubmit = useCallback(async (e: React.FormEvent) => {
        e.preventDefault()
        const trimmed = prompt.trim()
        if (!trimmed) { setErr('Enter a prompt'); return }
        if (trimmed.length > MAX_LEN) { setErr(`Max ${MAX_LEN} characters`); return }
        setErr('')
        setOpen(false)
        await submitEdit(trimmed)
    }, [prompt, submitEdit])
    const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => { setPrompt(e.target.value); if (err) setErr('') }, [err])
    return (
        <Popover open={open} onOpenChange={setOpen}>
            <Tooltip>
                <TooltipTrigger asChild>
                    <PopoverTrigger asChild>
                        <Button variant="ghost" size="icon" className={cn(btnCls, "quick-edit-btn")} disabled={!hasImg || isGenerating}>
                            {isGenerating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wand2 className="w-4 h-4" />}
                        </Button>
                    </PopoverTrigger>
                </TooltipTrigger>
                <TooltipContent side="top">{isGenerating ? 'Generating...' : 'Quick Edit'}</TooltipContent>
            </Tooltip>
            <PopoverContent side="top" sideOffset={16} className="w-96 p-0 border-0 bg-transparent shadow-none">
                <div className="group relative overflow-hidden rounded-xl border border-border/50 bg-background/95 backdrop-blur-xl shadow-2xl transition-all duration-300 ease-out">

                    <form onSubmit={handleSubmit} className="relative z-10 flex flex-col p-1.5">
                        <div className="relative flex items-center gap-2 rounded-lg bg-muted/30 px-2 py-1 transition-all focus-within:bg-muted/50">
                            <Input
                                ref={inputRef}
                                value={prompt}
                                onChange={handleChange}
                                placeholder="What do you want to update?"
                                maxLength={MAX_LEN}
                                className="h-10 flex-1 border-none bg-transparent px-2 text-sm font-medium placeholder:text-muted-foreground/50 focus-visible:ring-0"
                            />
                            <div className="flex items-center gap-1">
                                {prompt.trim() && (
                                    <Button
                                        type="submit"
                                        size="sm"
                                        className="h-7 w-7 rounded-md bg-indigo-500 hover:bg-indigo-600 text-white p-0 shadow-sm transition-all"
                                        disabled={!prompt.trim()}
                                    >
                                        <Wand2 className="w-3.5 h-3.5" />
                                    </Button>
                                )}
                            </div>
                        </div>

                        {err && <p className="ml-2 mt-1.5 text-xs font-medium text-rose-500 animate-in fade-in slide-in-from-top-1">{err}</p>}

                        <div className="flex items-center justify-end px-1 pt-1">
                            <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                onClick={() => setOpen(false)}
                                className="h-5 text-[10px] text-muted-foreground/60 hover:text-foreground px-2 py-0.5 rounded-full transition-colors"
                            >
                                Esc
                            </Button>
                        </div>
                    </form>
                </div>
            </PopoverContent>
        </Popover>)
}
