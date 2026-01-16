import{useState,useCallback,useEffect}from'react'
const STORAGE_KEY='sip-studio-unread-sessions'
function getStored():Set<string>{
  try{const v=localStorage.getItem(STORAGE_KEY);return v?new Set(JSON.parse(v)):new Set()}
  catch{return new Set()}
}
function setStored(ids:Set<string>){
  try{localStorage.setItem(STORAGE_KEY,JSON.stringify([...ids]))}catch{}
}
export function useUnreadSessions(){
  const[unreadIds,setUnreadIds]=useState<Set<string>>(()=>getStored())
  //Sync with localStorage on mount and across tabs
  useEffect(()=>{
    const handler=()=>setUnreadIds(getStored())
    window.addEventListener('storage',handler)
    return()=>window.removeEventListener('storage',handler)
  },[])
  const markUnread=useCallback((sessionId:string)=>{
    setUnreadIds(prev=>{
      if(prev.has(sessionId))return prev
      const next=new Set(prev).add(sessionId)
      setStored(next)
      return next
    })
  },[])
  const markRead=useCallback((sessionId:string)=>{
    setUnreadIds(prev=>{
      if(!prev.has(sessionId))return prev
      const next=new Set(prev)
      next.delete(sessionId)
      setStored(next)
      return next
    })
  },[])
  const clearAll=useCallback(()=>{
    setUnreadIds(new Set())
    setStored(new Set())
  },[])
  return{
    unreadSessionIds:unreadIds,
    hasUnread:unreadIds.size>0,
    isUnread:(id:string)=>unreadIds.has(id),
    markUnread,
    markRead,
    clearAll,
  }
}
