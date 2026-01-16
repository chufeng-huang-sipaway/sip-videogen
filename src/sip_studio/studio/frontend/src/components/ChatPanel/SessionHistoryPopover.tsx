
import { useCallback, useState } from 'react'
import { Trash2, Edit2, Check, Search } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Input } from '@/components/ui/input'
import type { ChatSessionMeta } from '@/lib/bridge'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'

// Relative time formatting using Intl.RelativeTimeFormat
function getRelativeTime(isoDate: string): string {
    const d = new Date(isoDate), now = new Date()
    const diffMs = now.getTime() - d.getTime()
    const diffSec = Math.floor(diffMs / 1000)
    const diffMin = Math.floor(diffSec / 60)
    const diffHr = Math.floor(diffMin / 60)
    const diffDay = Math.floor(diffHr / 24)
    const rtf = new Intl.RelativeTimeFormat('en', { numeric: 'auto' })
    if (diffMin < 1) return 'just now'
    if (diffMin < 60) return rtf.format(-diffMin, 'minute')
    if (diffHr < 24) return rtf.format(-diffHr, 'hour')
    if (diffDay < 7) return rtf.format(-diffDay, 'day')
    if (diffDay < 30) return rtf.format(-Math.floor(diffDay / 7), 'week')
    return rtf.format(-Math.floor(diffDay / 30), 'month')
}

interface SessionHistoryPopoverProps {
    children: React.ReactNode
    sessionsByDate: Record<string, ChatSessionMeta[]>
    activeSessionId: string | null
    onSwitchSession: (sessionId: string) => Promise<boolean>
    onDeleteSession: (sessionId: string) => Promise<boolean>
    onRenameSession: (sessionId: string, newTitle: string) => Promise<boolean>
    onCreateSession?: () => Promise<void>
    isLoading?: boolean
    isUnread?: (sessionId: string) => boolean
    onMarkRead?: (sessionId: string) => void
}

function SessionItem({ session, isActive, isUnread, onSwitch, onDelete, onRename }: { session: ChatSessionMeta; isActive: boolean; isUnread?: boolean; onSwitch: () => void; onDelete: () => void; onRename: (title: string) => void }) {
    const [isEditing, setIsEditing] = useState(false)
    const [editTitle, setEditTitle] = useState(session.title)
    const handleSaveTitle = () => { if (editTitle.trim() && editTitle !== session.title) onRename(editTitle.trim()); setIsEditing(false) }
    const handleKeyDown = (e: React.KeyboardEvent) => { if (e.key === 'Enter') handleSaveTitle(); else if (e.key === 'Escape') { setEditTitle(session.title); setIsEditing(false) } }

    return (
        <div
            className={`group relative p-2.5 rounded-lg cursor-pointer transition-all duration-200 border ${isActive
                    ? 'bg-primary/5 border-primary/10 shadow-[0_1px_3px_rgba(0,0,0,0.02)]'
                    : 'border-transparent hover:bg-secondary/50 hover:border-border/30'
                }`}
            onClick={isEditing ? undefined : onSwitch}
        >
            <div className="flex items-start gap-3">
                {isUnread&&!isActive&&<span className="absolute left-1.5 top-1/2 -translate-y-1/2 w-1.5 h-1.5 bg-blue-500 rounded-full"/>}
                <div className="flex-1 min-w-0">
                    {isEditing ? (
                        <div className="flex items-center gap-1" onClick={e => e.stopPropagation()}>
                            <Input
                                value={editTitle}
                                onChange={e => setEditTitle(e.target.value)}
                                onKeyDown={handleKeyDown}
                                onBlur={handleSaveTitle}
                                autoFocus
                                className="h-6 text-sm px-1 py-0 bg-transparent border-primary/50 focus-visible:ring-0"
                            />
                            <Button variant="ghost" size="sm" className="h-6 w-6 p-0 hover:text-primary" onClick={handleSaveTitle}>
                                <Check className="w-3.5 h-3.5" strokeWidth={1.5} />
                            </Button>
                        </div>
                    ) : (
                        <div className={`text-sm font-medium truncate transition-colors ${isActive ? 'text-foreground' : 'text-muted-foreground group-hover:text-foreground'}`}>
                            {session.title || 'New conversation'}
                        </div>
                    )}
                    <div className={`text-xs mt-0.5 transition-colors ${isActive ? 'text-primary/70' : 'text-muted-foreground/60 group-hover:text-muted-foreground'}`}>
                        {getRelativeTime(session.lastActiveAt)}
                    </div>
                </div>
                {!isEditing && (
                    <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity absolute right-2 top-2 bg-background/80 backdrop-blur-sm rounded-md shadow-sm border border-border/10 p-0.5">
                        <Button variant="ghost" size="sm" className="h-6 w-6 p-0 text-muted-foreground hover:text-foreground hover:bg-accent" onClick={(e) => { e.stopPropagation(); setEditTitle(session.title); setIsEditing(true) }}><Edit2 className="w-3 h-3" strokeWidth={1.5} /></Button>
                        <Button variant="ghost" size="sm" className="h-6 w-6 p-0 text-muted-foreground hover:text-destructive hover:bg-destructive/10" onClick={(e) => { e.stopPropagation(); onDelete() }}><Trash2 className="w-3 h-3" strokeWidth={1.5} /></Button>
                    </div>
                )}
            </div>
        </div>
    )
}

export function SessionHistoryPopover({ children, sessionsByDate, activeSessionId, onSwitchSession, onDeleteSession, onRenameSession, isLoading, isUnread, onMarkRead }: SessionHistoryPopoverProps) {
    const [open, setOpen] = useState(false)
    const [searchQuery, setSearchQuery] = useState('')

    const handleSwitch = useCallback(async (sessionId: string) => {
        const ok = await onSwitchSession(sessionId)
        if (ok) { onMarkRead?.(sessionId); setOpen(false) }
    }, [onSwitchSession, onMarkRead])

    const handleDelete = useCallback(async (sessionId: string) => {
        if (confirm('Delete this conversation?')) await onDeleteSession(sessionId)
    }, [onDeleteSession])

    const handleRename = useCallback(async (sessionId: string, title: string) => {
        await onRenameSession(sessionId, title)
    }, [onRenameSession])

    const dateGroups = Object.entries(sessionsByDate)

    // Filter logic could be added here if needed, currently just visual search input
    // simplistic filtering if we wanted:
    const filteredGroups = searchQuery ? dateGroups.map(([date, sessions]) => [date, sessions.filter(s => s.title.toLowerCase().includes(searchQuery.toLowerCase()))] as [string, ChatSessionMeta[]]).filter(([_, s]) => s.length > 0) : dateGroups

    return (
        <Popover open={open} onOpenChange={setOpen}>
            <PopoverTrigger asChild>
                {children}
            </PopoverTrigger>
            {/* Updated visual style: Standard PopoverContent colors, aligned with GenerationSettings */}
            <PopoverContent className="w-80 p-0 shadow-lg border-border/50" align="start" sideOffset={8}>
                <div className="p-3 border-b border-border/30 bg-muted/5">
                    <div className="relative group">
                        <Search className="absolute left-2.5 top-2 h-4 w-4 text-muted-foreground/60 transition-colors group-focus-within:text-foreground/60" strokeWidth={1.5} />
                        <Input
                            placeholder="Search conversations..."
                            className="h-8 pl-9 bg-background border-border/40 shadow-sm focus-visible:ring-1 focus-visible:ring-primary/20 transition-all placeholder:text-muted-foreground/50"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                        />
                    </div>
                </div>

                <ScrollArea className="h-[400px]">
                    <div className="p-2 space-y-4">
                        {isLoading ? (
                            <div className="flex flex-col items-center justify-center py-10 text-muted-foreground gap-2">
                                <div className="animate-spin rounded-full h-4 w-4 border-2 border-primary border-t-transparent" />
                                <span className="text-xs">Loading...</span>
                            </div>
                        ) : filteredGroups.length === 0 ? (
                            <div className="text-center py-10 text-muted-foreground">
                                <p className="text-xs">No conversations found</p>
                            </div>
                        ) : (
                            filteredGroups.map(([date, sessions]) => (
                                <div key={date} className="space-y-1">
                                    <div className="px-2.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-1 mt-2">{date}</div>
                                    <div className="space-y-0.5">
                                        {sessions.map(s => (
                                            <SessionItem key={s.id} session={s} isActive={s.id === activeSessionId} isUnread={isUnread?.(s.id)} onSwitch={() => handleSwitch(s.id)} onDelete={() => handleDelete(s.id)} onRename={t => handleRename(s.id, t)} />
                                        ))}
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </ScrollArea>
                {/* Optional footer to match GenerationSettings style if needed */}
                <div className="px-3 py-2 bg-muted/20 border-t border-border/30 text-[10px] text-muted-foreground/60 flex justify-between items-center">
                    <span>{Object.values(sessionsByDate).flat().length} conversations</span>
                </div>
            </PopoverContent>
        </Popover>
    )
}
