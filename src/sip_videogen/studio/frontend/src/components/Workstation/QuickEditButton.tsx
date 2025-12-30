//QuickEditButton - AI-powered image edit with popover input
import{useState,useCallback,useRef,useEffect}from'react'
import{useWorkstation}from'../../context/WorkstationContext'
import{Button}from'../ui/button'
import{Input}from'../ui/input'
import{Popover,PopoverTrigger,PopoverContent}from'../ui/popover'
import{Tooltip,TooltipContent,TooltipTrigger}from'../ui/tooltip'
import{Sparkles}from'lucide-react'
import{cn}from'@/lib/utils'
const MAX_LEN=500
interface QuickEditButtonProps{variant?:'light'|'dark'}
export function QuickEditButton({variant='dark'}:QuickEditButtonProps){
const{currentBatch,selectedIndex}=useWorkstation()
const curr=currentBatch[selectedIndex]
const hasImg=!!(curr?.originalPath||curr?.path)
const[open,setOpen]=useState(false)
const[prompt,setPrompt]=useState('')
const[err,setErr]=useState('')
const inputRef=useRef<HTMLInputElement>(null)
const isDark=variant==='dark'
const btnCls=cn("h-9 w-9 rounded-full transition-all",isDark?"text-white/90 hover:bg-white/10":"hover:bg-black/5 dark:hover:bg-white/10")
//Focus input on open
useEffect(()=>{if(open)setTimeout(()=>inputRef.current?.focus(),50)},[open])
//Reset on close
useEffect(()=>{if(!open){setPrompt('');setErr('')}},[open])
//Validate & submit
const handleSubmit=useCallback((e:React.FormEvent)=>{
e.preventDefault()
const trimmed=prompt.trim()
if(!trimmed){setErr('Enter a prompt');return}
if(trimmed.length>MAX_LEN){setErr(`Max ${MAX_LEN} characters`);return}
setErr('')
//TODO: Wire to QuickEditContext.submitEdit in Stage 2
console.log('QuickEdit submit:',trimmed)
setOpen(false)
},[prompt])
const handleChange=useCallback((e:React.ChangeEvent<HTMLInputElement>)=>{setPrompt(e.target.value);if(err)setErr('')},[err])
return(<Popover open={open} onOpenChange={setOpen}><Tooltip><TooltipTrigger asChild><PopoverTrigger asChild><Button variant="ghost" size="icon" className={cn(btnCls,"quick-edit-btn")} disabled={!hasImg}><Sparkles className="w-4 h-4"/></Button></PopoverTrigger></TooltipTrigger><TooltipContent side="top">Quick Edit</TooltipContent></Tooltip><PopoverContent side="top" className="w-80 p-3"><form onSubmit={handleSubmit} className="flex flex-col gap-2"><label className="text-xs font-medium text-muted-foreground">Describe the edit</label><Input ref={inputRef} value={prompt} onChange={handleChange} placeholder="e.g. make the background blue" maxLength={MAX_LEN} className="h-9"/>{err&&<p className="text-xs text-destructive">{err}</p>}<div className="flex justify-end gap-2 mt-1"><Button type="button" variant="ghost" size="sm" onClick={()=>setOpen(false)}>Cancel</Button><Button type="submit" size="sm" disabled={!prompt.trim()}>Edit</Button></div></form></PopoverContent></Popover>)
}
