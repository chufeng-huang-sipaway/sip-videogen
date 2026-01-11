import{useCallback,useState}from'react'
import{X,MessageSquare,Trash2,Edit2,Check}from'lucide-react'
import{Button}from'@/components/ui/button'
import{ScrollArea}from'@/components/ui/scroll-area'
import{Input}from'@/components/ui/input'
import type{ChatSessionMeta}from'@/lib/bridge'
//Relative time formatting using Intl.RelativeTimeFormat
function getRelativeTime(isoDate:string):string{
  const d=new Date(isoDate),now=new Date()
  const diffMs=now.getTime()-d.getTime()
  const diffSec=Math.floor(diffMs/1000)
  const diffMin=Math.floor(diffSec/60)
  const diffHr=Math.floor(diffMin/60)
  const diffDay=Math.floor(diffHr/24)
  const rtf=new Intl.RelativeTimeFormat('en',{numeric:'auto'})
  if(diffMin<1)return'just now'
  if(diffMin<60)return rtf.format(-diffMin,'minute')
  if(diffHr<24)return rtf.format(-diffHr,'hour')
  if(diffDay<7)return rtf.format(-diffDay,'day')
  if(diffDay<30)return rtf.format(-Math.floor(diffDay/7),'week')
  return rtf.format(-Math.floor(diffDay/30),'month')
}
interface SessionHistoryDrawerProps{
  isOpen:boolean
  onClose:()=>void
  sessionsByDate:Record<string,ChatSessionMeta[]>
  activeSessionId:string|null
  onSwitchSession:(sessionId:string)=>Promise<boolean>
  onDeleteSession:(sessionId:string)=>Promise<boolean>
  onRenameSession:(sessionId:string,newTitle:string)=>Promise<boolean>
  onCreateSession:()=>Promise<void>
  isLoading?:boolean
}
function SessionItem({session,isActive,onSwitch,onDelete,onRename}:{session:ChatSessionMeta;isActive:boolean;onSwitch:()=>void;onDelete:()=>void;onRename:(title:string)=>void}){
  const[isEditing,setIsEditing]=useState(false)
  const[editTitle,setEditTitle]=useState(session.title)
  const handleSaveTitle=()=>{if(editTitle.trim()&&editTitle!==session.title)onRename(editTitle.trim());setIsEditing(false)}
  const handleKeyDown=(e:React.KeyboardEvent)=>{if(e.key==='Enter')handleSaveTitle();else if(e.key==='Escape'){setEditTitle(session.title);setIsEditing(false)}}
  return(
    <div className={`group p-3 rounded-lg cursor-pointer transition-colors ${isActive?'bg-primary/10 border border-primary/20':'hover:bg-muted/50'}`} onClick={isEditing?undefined:onSwitch}>
      <div className="flex items-start gap-2">
        <MessageSquare className="w-4 h-4 mt-0.5 text-muted-foreground shrink-0"/>
        <div className="flex-1 min-w-0">
          {isEditing?(
            <div className="flex items-center gap-1" onClick={e=>e.stopPropagation()}>
              <Input value={editTitle} onChange={e=>setEditTitle(e.target.value)} onKeyDown={handleKeyDown} onBlur={handleSaveTitle} autoFocus className="h-6 text-sm px-1 py-0"/>
              <Button variant="ghost" size="sm" className="h-6 w-6 p-0" onClick={handleSaveTitle}><Check className="w-3 h-3"/></Button>
            </div>
          ):(
            <div className="font-medium text-sm truncate">{session.title||'New conversation'}</div>
          )}
          <div className="text-xs text-muted-foreground">{getRelativeTime(session.lastActiveAt)}</div>
        </div>
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity" onClick={e=>e.stopPropagation()}>
          <Button variant="ghost" size="sm" className="h-6 w-6 p-0" onClick={()=>{setEditTitle(session.title);setIsEditing(true)}}><Edit2 className="w-3 h-3"/></Button>
          <Button variant="ghost" size="sm" className="h-6 w-6 p-0 text-destructive hover:text-destructive" onClick={onDelete}><Trash2 className="w-3 h-3"/></Button>
        </div>
      </div>
    </div>
  )
}
export function SessionHistoryDrawer({isOpen,onClose,sessionsByDate,activeSessionId,onSwitchSession,onDeleteSession,onRenameSession,isLoading}:SessionHistoryDrawerProps){
  const handleSwitch=useCallback(async(sessionId:string)=>{const ok=await onSwitchSession(sessionId);if(ok)onClose()},[onSwitchSession,onClose])
  const handleDelete=useCallback(async(sessionId:string)=>{if(confirm('Delete this conversation?'))await onDeleteSession(sessionId)},[onDeleteSession])
  const handleRename=useCallback(async(sessionId:string,title:string)=>{await onRenameSession(sessionId,title)},[onRenameSession])
  if(!isOpen)return null
  const dateGroups=Object.entries(sessionsByDate)
  return(
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/20 z-40" onClick={onClose}/>
      {/* Drawer */}
      <div className="fixed left-0 top-0 h-full w-80 bg-background border-r border-border z-50 shadow-xl animate-in slide-in-from-left duration-200">
        <div className="flex items-center justify-between px-4 py-3 border-b border-border">
          <h2 className="font-semibold text-sm">Chat History</h2>
          <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={onClose}><X className="w-4 h-4"/></Button>
        </div>
        <ScrollArea className="h-[calc(100%-50px)]">
          <div className="p-3 space-y-4">
            {isLoading?(
              <div className="text-sm text-muted-foreground text-center py-4">Loading...</div>
            ):dateGroups.length===0?(
              <div className="text-sm text-muted-foreground text-center py-4">No conversations yet</div>
            ):(
              dateGroups.map(([date,sessions])=>(
                <div key={date}>
                  <div className="text-xs font-medium text-muted-foreground mb-2 px-1">{date}</div>
                  <div className="space-y-1">
                    {sessions.map(s=>(
                      <SessionItem key={s.id} session={s} isActive={s.id===activeSessionId} onSwitch={()=>handleSwitch(s.id)} onDelete={()=>handleDelete(s.id)} onRename={t=>handleRename(s.id,t)}/>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
        </ScrollArea>
      </div>
    </>
  )
}
