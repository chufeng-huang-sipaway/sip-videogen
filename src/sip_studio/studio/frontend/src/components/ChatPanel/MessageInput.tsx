import { useEffect, useRef, useState, useCallback, forwardRef, useImperativeHandle, type ReactNode } from 'react'
import { ArrowUp, Plus, Image, Square, Loader2, Globe, Telescope } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { QuickInsertPopover } from './QuickInsertPopover'
import { MentionAutocomplete, type MentionAutocompleteRef } from './MentionAutocomplete'
import { cn } from '@/lib/utils'
import { isValidTriggerPosition } from '@/lib/mentionParser'
//Toggle button with expand animation (icon → icon + label when active)
interface ToggleBtnProps {icon:ReactNode;label:string;active:boolean;onClick?:()=>void;disabled?:boolean}
function ToggleBtn({icon,label,active,onClick,disabled}:ToggleBtnProps){
	return(
		<button onClick={onClick} disabled={disabled} className={cn(
			"inline-flex items-center gap-1.5 h-8 rounded-full transition-all duration-200 ease-out",
			"text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed",
			active?"bg-brand-500/15 text-brand-500 hover:bg-brand-500/25 pl-2.5 pr-3":"text-muted-foreground hover:text-foreground hover:bg-muted/50 px-2"
		)}>
			<span className="shrink-0 w-4 h-4 flex items-center justify-center">{icon}</span>
			<span className={cn(
				"overflow-hidden whitespace-nowrap transition-all duration-200 ease-out",
				active?"max-w-[80px] opacity-100":"max-w-0 opacity-0"
			)}>{label}</span>
		</button>
	)
}
interface MessageInputProps {
	disabled?: boolean
	placeholder?: string
	onSend: (text: string) => void
	canSendWithoutText?: boolean
	onSelectImages?: (files: File[]) => void
	hasProducts?: boolean
	hasStyleReferences?: boolean
	isGenerating?: boolean
	onCancel?: () => void
	onMessageChange?: (text: string) => void
	webSearchEnabled?: boolean
	deepResearchEnabled?: boolean
	onWebSearchToggle?: () => void
	onDeepResearchToggle?: () => void
}
export interface MessageInputRef { focus: () => void }
//Dynamic placeholder based on mode
function getPlaceholder(webSearch:boolean,deepResearch:boolean,fallback?:string){
	if(deepResearch)return"Get a detailed research report"
	if(webSearch)return"Search the web"
	return fallback||"Ask anything"
}
export const MessageInput = forwardRef<MessageInputRef, MessageInputProps>(function MessageInput({ disabled, placeholder, onSend, canSendWithoutText = false, onSelectImages, hasProducts = false, hasStyleReferences = false, isGenerating = false, onCancel, onMessageChange, webSearchEnabled = false, deepResearchEnabled = false, onWebSearchToggle, onDeepResearchToggle }, ref) {
	const [message, setMessage] = useState('')
	const [popoverOpen, setPopoverOpen] = useState(false)
	const [showMention, setShowMention] = useState(false)
	const [caretPos, setCaretPos] = useState(0)
	const textareaRef = useRef<HTMLTextAreaElement>(null)
	const fileInputRef = useRef<HTMLInputElement>(null)
	const mentionRef = useRef<MentionAutocompleteRef>(null)
	//Expose focus method to parent
	useImperativeHandle(ref, () => ({ focus: () => textareaRef.current?.focus() }), [])
	const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
		const files = e.target.files
		if (files && files.length > 0 && onSelectImages) onSelectImages(Array.from(files))
		//Reset input so same file can be selected again
		e.target.value = ''
	}
	useEffect(() => {
		const el = textareaRef.current
		if (!el) return
		el.style.height = 'auto'
		el.style.height = `${Math.min(el.scrollHeight, 160)}px`
	}, [message])
	//Check for @ trigger on input change
	const handleChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
		const val = e.target.value
		const pos = e.target.selectionStart || 0
		setMessage(val)
		setCaretPos(pos)
		onMessageChange?.(val)
		//Check if we just typed @ at valid position
		if (isValidTriggerPosition(val, pos)) { setShowMention(true) }
		//Close autocomplete if we deleted the @
		else if (showMention) {
			//Check if still in a mention context
			let hasAt = false
			for (let i = pos - 1; i >= 0; i--) {
				if (val[i] === '@') { hasAt = true; break }
				if (/\s/.test(val[i])) break
			}
			if (!hasAt) setShowMention(false)
		}
	}, [showMention, onMessageChange])
	//Track caret position on selection change
	const handleSelect = useCallback(() => {
		const el = textareaRef.current
		if (el) setCaretPos(el.selectionStart || 0)
	}, [])
	//Handle mention selection - insert @type:slug at position
	const handleMentionSelect = useCallback((type: 'product' | 'style', slug: string, start: number) => {
		const before = message.slice(0, start)
		const after = message.slice(caretPos)
		const mention = `@${type}:${slug} `
		const newMsg = before + mention + after
		setMessage(newMsg)
		onMessageChange?.(newMsg)
		setShowMention(false)
		//Set caret after inserted mention
		setTimeout(() => {
			const el = textareaRef.current
			if (el) {
				const newPos = start + mention.length
				el.setSelectionRange(newPos, newPos)
				el.focus()
			}
		}, 0)
	}, [message, caretPos, onMessageChange])
	const closeMention = useCallback(() => setShowMention(false), [])
	const submit = () => {
		const text = message.trim()
		if (!text && !canSendWithoutText) return
		if (disabled) return
		onSend(text)
		setMessage('')
		setShowMention(false)
		onMessageChange?.('')
	}
	const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
		//Don't handle during IME composition
		if (e.nativeEvent.isComposing) return
		//Let mention autocomplete handle keys when open
		if (showMention && mentionRef.current?.handleKeyDown(e)) return
		//Normal submit on Enter (not during popover)
		if (e.key === 'Enter' && !e.shiftKey && !popoverOpen) { e.preventDefault(); submit() }
	}
	const showQuickInsert = hasProducts || hasStyleReferences
	const dynamicPlaceholder = getPlaceholder(webSearchEnabled,deepResearchEnabled,placeholder)
	return (
		<div className="relative w-full group">
			{/* Mention autocomplete dropdown */}
			{showMention && (
				<MentionAutocomplete
					ref={mentionRef}
					text={message}
					caretPos={caretPos}
					onSelect={handleMentionSelect}
					onClose={closeMention}
				/>
			)}

			<div className={cn(
				"relative flex flex-col rounded-3xl bg-background/80 backdrop-blur-md shadow-lg border border-white/20 transition-all duration-300",
				"focus-within:shadow-[0_8px_30px_rgba(0,0,0,0.12)] focus-within:bg-background focus-within:border-white/40",
				"dark:bg-neutral-900/80 dark:border-white/10 dark:focus-within:bg-neutral-900 dark:focus-within:border-white/20"
			)}>
				{/* Hidden file input for image selection */}
				<input
					ref={fileInputRef}
					type="file"
					accept="image/*"
					multiple
					className="hidden"
					onChange={handleFileSelect}
				/>

				{/* Textarea - top section */}
				<textarea
					ref={textareaRef}
					value={message}
					onChange={handleChange}
					onSelect={handleSelect}
					onKeyDown={handleKeyDown}
					placeholder={dynamicPlaceholder}
					disabled={disabled}
					rows={1}
					className="flex-1 max-h-[160px] resize-none bg-transparent py-3 px-4 text-sm placeholder:text-muted-foreground/50 focus:outline-none disabled:opacity-50 min-h-[44px] leading-relaxed"
				/>

				{/* Button row - bottom section */}
				<div className="flex items-center justify-between px-2 pb-2 pt-0">
					{/* Left actions */}
					<div className="flex items-center gap-1">
						{/* Attachment Menu - Show QuickInsert when products/style references exist */}
						{showQuickInsert ? (
							<QuickInsertPopover
								open={popoverOpen}
								onOpenChange={setPopoverOpen}
								onUploadImage={onSelectImages ? () => fileInputRef.current?.click() : undefined}
								trigger={
									<Button variant="ghost" size="icon" className="h-8 w-8 shrink-0 rounded-full text-muted-foreground hover:bg-muted/50 hover:text-foreground transition-all" disabled={disabled}>
										<Plus className="h-4 w-4" strokeWidth={1.5} />
									</Button>
								}
							/>
						) : (
							<DropdownMenu>
								<DropdownMenuTrigger asChild>
									<Button variant="ghost" size="icon" className="h-8 w-8 shrink-0 rounded-full text-muted-foreground hover:bg-muted/50 hover:text-foreground transition-all" disabled={disabled}>
										<Plus className="h-4 w-4" strokeWidth={1.5} />
									</Button>
								</DropdownMenuTrigger>
								<DropdownMenuContent align="start" className="w-48 rounded-2xl shadow-float border-border/20 p-1.5" sideOffset={10}>
									<DropdownMenuItem onClick={() => fileInputRef.current?.click()} className="cursor-pointer gap-2 py-2.5 rounded-xl text-xs font-medium">
										<Image className="h-4 w-4 opacity-70" strokeWidth={1.5} />
										Upload Image
									</DropdownMenuItem>
								</DropdownMenuContent>
							</DropdownMenu>
						)}

						{/* Research toggle buttons with expand animation */}
						<ToggleBtn
							icon={<Globe className="h-4 w-4" strokeWidth={1.5}/>}
							label="Search"
							active={webSearchEnabled}
							onClick={onWebSearchToggle}
							disabled={disabled}
						/>
						<ToggleBtn
							icon={<Telescope className="h-4 w-4" strokeWidth={1.5}/>}
							label="Research"
							active={deepResearchEnabled}
							onClick={onDeepResearchToggle}
							disabled={disabled}
						/>
					</div>

					{/* Right actions - send/cancel button */}
					<div className="flex items-center shrink-0">
						{isGenerating ? (
							<Button type="button" size="icon" onClick={onCancel} className="h-8 w-8 rounded-full shrink-0 transition-all duration-200 bg-destructive text-destructive-foreground hover:bg-destructive/90 active:scale-95 shadow-sm hover:shadow-md" title="Cancel generation">
								<div className="relative">
									<Loader2 className="h-4 w-4 animate-spin absolute inset-0 opacity-30" strokeWidth={1.5}/>
									<Square className="h-2.5 w-2.5" strokeWidth={1.5} fill="currentColor"/>
								</div>
							</Button>
						) : (
							<Button type="button" size="icon" onClick={submit} disabled={disabled || (!message.trim() && !canSendWithoutText)} className={cn(
								"h-8 w-8 rounded-full shrink-0 transition-all duration-300",
								"bg-brand-500 text-white hover:bg-brand-600 active:scale-95",
								"shadow-[0_0_20px_rgba(237,9,66,0.3)] hover:shadow-[0_0_25px_rgba(237,9,66,0.5)]",
								"disabled:opacity-20 disabled:bg-muted disabled:text-muted-foreground disabled:shadow-none"
							)}>
								<ArrowUp className="h-4 w-4" strokeWidth={1.5}/>
							</Button>
						)}
					</div>
				</div>
			</div>
		</div>
	)
})
