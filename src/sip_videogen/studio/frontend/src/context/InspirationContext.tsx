import{createContext,useContext,type ReactNode}from'react'
import{useInspirations}from'@/hooks/useInspirations'
import type{Inspiration}from'@/lib/bridge'
interface InspirationContextValue{
inspirations:Inspiration[]
isGenerating:boolean
jobId:string|null
progress:number
error:string|null
newCount:number
viewedIds:Set<string>
triggerGeneration:()=>Promise<void>
save:(inspirationId:string,imageIdx:number,projectSlug?:string|null)=>Promise<void>
dismiss:(inspirationId:string)=>Promise<void>
moreLikeThis:(inspirationId:string)=>Promise<void>
markViewed:(inspirationId:string)=>void
refresh:()=>Promise<void>
cancelCurrentJob:()=>Promise<void>
}
const InspirationContext=createContext<InspirationContextValue|null>(null)
interface InspirationProviderProps{brandSlug:string|null;children:ReactNode}
export function InspirationProvider({brandSlug,children}:InspirationProviderProps){
const value=useInspirations(brandSlug)
return<InspirationContext.Provider value={value}>{children}</InspirationContext.Provider>
}
export function useInspirationContext():InspirationContextValue{
const ctx=useContext(InspirationContext)
if(!ctx)throw new Error('useInspirationContext must be used within InspirationProvider')
return ctx
}
