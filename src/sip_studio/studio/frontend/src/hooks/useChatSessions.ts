import{useState,useCallback,useEffect}from'react'
import{bridge,isPyWebView,waitForPyWebViewReady,type ChatSessionMeta}from'@/lib/bridge'
/**Groups sessions by date category (Today, Yesterday, This Week, Older).
 *Backend guarantees ISO timestamps with Z suffix (UTC).*/
function groupByDate(sessions:ChatSessionMeta[]):Record<string,ChatSessionMeta[]>{
  const now=new Date()
  const todayUTC=Date.UTC(now.getUTCFullYear(),now.getUTCMonth(),now.getUTCDate())
  const yesterdayUTC=todayUTC-24*60*60*1000
  const weekAgoUTC=todayUTC-7*24*60*60*1000
  const groups:Record<string,ChatSessionMeta[]>={'Today':[],'Yesterday':[],'This Week':[],'Older':[]}
  for(const s of sessions){
    const d=new Date(s.lastActiveAt)
    const dUTC=Date.UTC(d.getUTCFullYear(),d.getUTCMonth(),d.getUTCDate())
    if(dUTC>=todayUTC)groups['Today'].push(s)
    else if(dUTC>=yesterdayUTC)groups['Yesterday'].push(s)
    else if(dUTC>=weekAgoUTC)groups['This Week'].push(s)
    else groups['Older'].push(s)
  }
  return Object.fromEntries(Object.entries(groups).filter(([_,v])=>v.length>0))
}
export function useChatSessions(brandSlug:string|null){
  const[sessions,setSessions]=useState<ChatSessionMeta[]>([])
  const[activeSessionId,setActiveSessionId]=useState<string|null>(null)
  const[isLoading,setIsLoading]=useState(false)
  const[error,setError]=useState<string|null>(null)
  const refresh=useCallback(async()=>{
    if(!brandSlug){setSessions([]);setActiveSessionId(null);return}
    setIsLoading(true);setError(null)
    try{
      const ready=await waitForPyWebViewReady()
      if(!ready){
        //Mock data for dev
        setSessions([{id:'mock-1',brandSlug,title:'Mock Session',createdAt:'2026-01-10T12:00:00Z',lastActiveAt:'2026-01-10T12:00:00Z',updatedAt:'2026-01-10T12:00:00Z',messageCount:5,preview:'Hello world...',isArchived:false}])
        setActiveSessionId('mock-1')
        return
      }
      const list=await bridge.listSessions(brandSlug,false)
      setSessions(list)
      //Don't auto-select session on load - start with empty chat, no highlight
    }catch(e){setError(e instanceof Error?e.message:'Failed to load sessions')}
    finally{setIsLoading(false)}
  },[brandSlug])
  const createSession=useCallback(async(title?:string):Promise<ChatSessionMeta|null>=>{
    if(!brandSlug||!isPyWebView())return null
    try{
      const session=await bridge.createSession(title)
      setActiveSessionId(session.id)
      await refresh()
      return session
    }catch(e){setError(e instanceof Error?e.message:'Failed to create session');return null}
  },[brandSlug,refresh])
  const switchSession=useCallback(async(sessionId:string):Promise<boolean>=>{
    if(!brandSlug||!isPyWebView())return false
    try{
      await bridge.setActiveSession(sessionId)
      setActiveSessionId(sessionId)
      return true
    }catch(e){setError(e instanceof Error?e.message:'Failed to switch session');return false}
  },[brandSlug])
  const deleteSession=useCallback(async(sessionId:string):Promise<boolean>=>{
    if(!brandSlug||!isPyWebView())return false
    try{
      await bridge.deleteSession(sessionId)
      if(activeSessionId===sessionId)setActiveSessionId(null)
      await refresh()
      return true
    }catch(e){setError(e instanceof Error?e.message:'Failed to delete session');return false}
  },[brandSlug,activeSessionId,refresh])
  const renameSession=useCallback(async(sessionId:string,newTitle:string):Promise<boolean>=>{
    if(!brandSlug||!isPyWebView())return false
    try{
      await bridge.updateSession(sessionId,newTitle)
      await refresh()
      return true
    }catch(e){setError(e instanceof Error?e.message:'Failed to rename session');return false}
  },[brandSlug,refresh])
  //Load on mount and when brand changes
  useEffect(()=>{refresh()},[refresh])
  const sessionsByDate=groupByDate(sessions)
  return{sessions,sessionsByDate,activeSessionId,isLoading,error,refresh,createSession,switchSession,deleteSession,renameSession}
}
