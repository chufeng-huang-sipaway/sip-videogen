//QuickEditButton - AI-powered image edit with popover input
import{useState,useCallback,useRef,useEffect}from'react'
import{useWorkstation}from'../../context/WorkstationContext'
import{useQuickEdit}from'../../context/QuickEditContext'
import{getMediaType}from'../../lib/mediaUtils'
import{Button}from'../ui/button'
import{Input}from'../ui/input'
import{Popover,PopoverTrigger,PopoverContent}from'../ui/popover'
import{Tooltip,TooltipContent,TooltipTrigger}from'../ui/tooltip'
import{Wand2,Loader2}from'lucide-react'
import{cn}from'@/lib/utils'
const MAX_LEN = 500
interface QuickEditButtonProps { variant?: 'light' | 'dark' }
export function QuickEditButton({ }: QuickEditButtonProps) {
    const { currentBatch, selectedIndex } = useWorkstation()
    const { isGenerating, submitEdit, error: ctxError, clearError, prompt: ctxPrompt, resultPath } = useQuickEdit()
    const curr=currentBatch[selectedIndex]
    const imgPath=curr?.originalPath||curr?.path||''
    const isVideo=curr?getMediaType(curr)==='video':false
    const hasImg=!!imgPath&&!isVideo
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
                <form onSubmit={handleSubmit} className="relative rounded-2xl bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 shadow-sm">
                    <Input ref={inputRef} value={prompt} onChange={handleChange} placeholder="What do you want to update?" maxLength={MAX_LEN} className="h-auto min-h-[90px] border-none bg-transparent px-4 pt-4 pb-12 text-[13px] placeholder:text-neutral-400 focus-visible:ring-0"/>
                    {err&&<p className="absolute left-4 bottom-12 text-xs text-brand-500">{err}</p>}
                    <div className="absolute right-3 bottom-3"><Button type="submit" size="sm" className={cn("h-8 px-3 rounded-lg text-xs font-medium transition-all",prompt.trim()?"bg-neutral-200 dark:bg-neutral-700 hover:bg-neutral-300 dark:hover:bg-neutral-600 text-neutral-600 dark:text-neutral-300":"bg-neutral-100 dark:bg-neutral-800 text-neutral-300 dark:text-neutral-600 cursor-not-allowed")} disabled={!prompt.trim()}><Wand2 className="w-3.5 h-3.5 mr-1.5"/>Edit</Button></div>
                </form>
            </PopoverContent>
        </Popover>)
}
