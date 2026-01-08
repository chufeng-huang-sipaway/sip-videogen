//QuickGeneratorContext - provides quick generator state and send-to-chat callback
import{createContext,useContext,useCallback,useState,type ReactNode}from'react'
import{useQuickGenerator,type UseQuickGeneratorResult}from'@/hooks/useQuickGenerator'
interface QuickGeneratorContextValue extends UseQuickGeneratorResult{
sendToChat:(paths:string[])=>void
registerSendToChat:(fn:(paths:string[])=>void)=>void}
const QuickGeneratorContext=createContext<QuickGeneratorContextValue|null>(null)
export function QuickGeneratorProvider({children}:{children:ReactNode}){
const generator=useQuickGenerator()
const[sendFn,setSendFn]=useState<((paths:string[])=>void)|null>(null)
const registerSendToChat=useCallback((fn:(paths:string[])=>void)=>{setSendFn(()=>fn)},[])
const sendToChat=useCallback((paths:string[])=>{
if(sendFn)sendFn(paths)
generator.close()
},[sendFn,generator])
return(<QuickGeneratorContext.Provider value={{...generator,sendToChat,registerSendToChat}}>
{children}
</QuickGeneratorContext.Provider>)}
export function useQuickGeneratorContext():QuickGeneratorContextValue{
const ctx=useContext(QuickGeneratorContext)
if(!ctx)throw new Error('useQuickGeneratorContext must be used within QuickGeneratorProvider')
return ctx}
