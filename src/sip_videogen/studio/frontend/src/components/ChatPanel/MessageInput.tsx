import{useEffect,useRef,useState,useCallback}from'react'
import{ArrowUp,Plus,Image,Square,Loader2}from'lucide-react'
import{Button}from'@/components/ui/button'
import{DropdownMenu,DropdownMenuContent,DropdownMenuItem,DropdownMenuTrigger}from'@/components/ui/dropdown-menu'
import{QuickInsertPopover}from'./QuickInsertPopover'
import{MentionAutocomplete,type MentionAutocompleteRef}from'./MentionAutocomplete'
import{cn}from'@/lib/utils'
import{isValidTriggerPosition}from'@/lib/mentionParser'
interface MessageInputProps{
disabled?:boolean
placeholder?:string
onSend:(text:string)=>void
canSendWithoutText?:boolean
onSelectImages?:(files:File[])=>void
hasProducts?:boolean
hasTemplates?:boolean
isGenerating?:boolean
onCancel?:()=>void
onMessageChange?:(text:string)=>void}
export function MessageInput({disabled,placeholder,onSend,canSendWithoutText=false,onSelectImages,hasProducts=false,hasTemplates=false,isGenerating=false,onCancel,onMessageChange}:MessageInputProps){
const[message,setMessage]=useState('')
const[popoverOpen,setPopoverOpen]=useState(false)
const[showMention,setShowMention]=useState(false)
const[caretPos,setCaretPos]=useState(0)
const textareaRef=useRef<HTMLTextAreaElement>(null)
const fileInputRef=useRef<HTMLInputElement>(null)
const mentionRef=useRef<MentionAutocompleteRef>(null)
const handleFileSelect=(e:React.ChangeEvent<HTMLInputElement>)=>{
const files=e.target.files
if(files&&files.length>0&&onSelectImages)onSelectImages(Array.from(files))
//Reset input so same file can be selected again
e.target.value=''}
useEffect(()=>{
const el=textareaRef.current
if(!el)return
el.style.height='auto'
el.style.height=`${Math.min(el.scrollHeight,160)}px`},[message])
//Check for @ trigger on input change
const handleChange=useCallback((e:React.ChangeEvent<HTMLTextAreaElement>)=>{
const val=e.target.value
const pos=e.target.selectionStart||0
setMessage(val)
setCaretPos(pos)
onMessageChange?.(val)
//Check if we just typed @ at valid position
if(isValidTriggerPosition(val,pos)){setShowMention(true)}
//Close autocomplete if we deleted the @
else if(showMention){
//Check if still in a mention context
let hasAt=false
for(let i=pos-1;i>=0;i--){
if(val[i]==='@'){hasAt=true;break}
if(/\s/.test(val[i]))break}
if(!hasAt)setShowMention(false)}},[showMention,onMessageChange])
//Track caret position on selection change
const handleSelect=useCallback(()=>{
const el=textareaRef.current
if(el)setCaretPos(el.selectionStart||0)},[])
//Handle mention selection - insert @type:slug at position
const handleMentionSelect=useCallback((type:'product'|'template',slug:string,start:number)=>{
const before=message.slice(0,start)
const after=message.slice(caretPos)
const mention=`@${type}:${slug} `
const newMsg=before+mention+after
setMessage(newMsg)
onMessageChange?.(newMsg)
setShowMention(false)
//Set caret after inserted mention
setTimeout(()=>{
const el=textareaRef.current
if(el){
const newPos=start+mention.length
el.setSelectionRange(newPos,newPos)
el.focus()}},0)},[message,caretPos,onMessageChange])
const closeMention=useCallback(()=>setShowMention(false),[])
const submit=()=>{
const text=message.trim()
if(!text&&!canSendWithoutText)return
if(disabled)return
onSend(text)
setMessage('')
setShowMention(false)
onMessageChange?.('')}
const handleKeyDown=(e:React.KeyboardEvent<HTMLTextAreaElement>)=>{
//Don't handle during IME composition
if(e.nativeEvent.isComposing)return
//Let mention autocomplete handle keys when open
if(showMention&&mentionRef.current?.handleKeyDown(e))return
//Normal submit on Enter (not during popover)
if(e.key==='Enter'&&!e.shiftKey&&!popoverOpen){e.preventDefault();submit()}}
const showQuickInsert=hasProducts||hasTemplates
return(
<div className="relative w-full">
{/* Mention autocomplete dropdown */}
{showMention&&<MentionAutocomplete ref={mentionRef} text={message} caretPos={caretPos} onSelect={handleMentionSelect} onClose={closeMention}/>}
<div className={cn("relative flex items-center gap-2 p-2 rounded-[26px] bg-background shadow-float border border-black/8 dark:border-white/10 transition-shadow duration-300","focus-within:shadow-xl focus-within:border-black/15 dark:focus-within:border-white/20")}>
{/* Hidden file input for image selection */}
<input ref={fileInputRef} type="file" accept="image/*" multiple className="hidden" onChange={handleFileSelect}/>
{/* Attachment Menu - Show QuickInsert when products/templates exist */}
{showQuickInsert?(
<QuickInsertPopover open={popoverOpen} onOpenChange={setPopoverOpen} onUploadImage={onSelectImages?()=>fileInputRef.current?.click():undefined} trigger={
<Button variant="ghost" size="icon" className="h-10 w-10 shrink-0 rounded-full text-muted-foreground hover:bg-muted/50 transition-colors" disabled={disabled}>
<Plus className="h-5 w-5" strokeWidth={1.5}/>
</Button>}/>
):(
<DropdownMenu>
<DropdownMenuTrigger asChild>
<Button variant="ghost" size="icon" className="h-10 w-10 shrink-0 rounded-full text-muted-foreground hover:bg-muted/50 transition-colors" disabled={disabled}>
<Plus className="h-5 w-5" strokeWidth={1.5}/>
</Button>
</DropdownMenuTrigger>
<DropdownMenuContent align="start" className="w-48 rounded-2xl shadow-float border-border/20 p-1.5" sideOffset={10}>
<DropdownMenuItem onClick={()=>fileInputRef.current?.click()} className="cursor-pointer gap-2 py-2.5 rounded-xl text-xs font-medium">
<Image className="h-4 w-4 opacity-70"/>Upload Image
</DropdownMenuItem>
</DropdownMenuContent>
</DropdownMenu>)}
<textarea ref={textareaRef} value={message} onChange={handleChange} onSelect={handleSelect} onKeyDown={handleKeyDown} placeholder={placeholder||'Type @ to mention products or templates'} disabled={disabled} rows={1} className="flex-1 max-h-[160px] resize-none bg-transparent py-2.5 text-sm placeholder:text-muted-foreground/50 focus:outline-none disabled:opacity-50 min-h-[40px] leading-relaxed"/>
<div className="flex items-center shrink-0">
{isGenerating?(
<Button type="button" size="icon" onClick={onCancel} className="h-10 w-10 rounded-full shrink-0 transition-all duration-200 bg-destructive text-destructive-foreground hover:bg-destructive/90 active:scale-95 shadow-sm" title="Cancel generation">
<div className="relative">
<Loader2 className="h-5 w-5 animate-spin absolute inset-0 opacity-30" strokeWidth={2}/>
<Square className="h-3 w-3" strokeWidth={2} fill="currentColor"/>
</div>
</Button>
):(
<Button type="button" size="icon" onClick={submit} disabled={disabled||(!message.trim()&&!canSendWithoutText)} className="h-10 w-10 rounded-full shrink-0 transition-all duration-200 bg-foreground text-background hover:bg-foreground/90 active:scale-95 disabled:opacity-20 disabled:bg-muted disabled:text-muted-foreground shadow-sm">
<ArrowUp className="h-5 w-5" strokeWidth={2}/>
</Button>)}
</div>
</div>
</div>)}
