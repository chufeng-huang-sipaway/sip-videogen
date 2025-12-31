import{createContext,useContext,useState,useEffect,type ReactNode}from'react'
const STORAGE_KEY='sip-studio-gallery-mode'
export type GalleryContentMode='assets'|'ideas'
interface GalleryModeContextValue{
contentMode:GalleryContentMode
setContentMode:(mode:GalleryContentMode)=>void
toggleMode:()=>void
}
const GalleryModeContext=createContext<GalleryModeContextValue|null>(null)
interface GalleryModeProviderProps{children:ReactNode}
export function GalleryModeProvider({children}:GalleryModeProviderProps){
const[contentMode,setContentModeState]=useState<GalleryContentMode>(()=>{
const stored=localStorage.getItem(STORAGE_KEY)
return(stored==='assets'||stored==='ideas')?stored:'assets'
})
useEffect(()=>{localStorage.setItem(STORAGE_KEY,contentMode)},[contentMode])
const setContentMode=(mode:GalleryContentMode)=>setContentModeState(mode)
const toggleMode=()=>setContentModeState(prev=>prev==='assets'?'ideas':'assets')
return<GalleryModeContext.Provider value={{contentMode,setContentMode,toggleMode}}>{children}</GalleryModeContext.Provider>
}
export function useGalleryMode():GalleryModeContextValue{
const ctx=useContext(GalleryModeContext)
if(!ctx)throw new Error('useGalleryMode must be used within GalleryModeProvider')
return ctx
}
