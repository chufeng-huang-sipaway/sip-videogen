/* eslint-disable react-refresh/only-export-components */
import{createContext,useContext,useState,useCallback,useRef,useEffect}from'react'
import type{ReactNode}from'react'
import{bridge}from'../lib/bridge'
import{useWorkstation}from'./WorkstationContext'
import{useBrand}from'./BrandContext'
//Generate unique request ID with fallback for older runtimes
const genId=()=>crypto.randomUUID?.()??`${Date.now()}-${Math.random().toString(36).slice(2)}`
//Quick edit state interface
interface QuickEditState{isGenerating:boolean;originalPath:string|null;resultPath:string|null;prompt:string;error:string|null}
interface QuickEditContextType extends QuickEditState{startEdit:(path:string)=>void;submitEdit:(prompt:string)=>Promise<void>;cancelEdit:()=>void;acceptResult:()=>void;discardResult:()=>Promise<void>;clearError:()=>void}
const QuickEditContext=createContext<QuickEditContextType|null>(null)
export function QuickEditProvider({children}:{children:ReactNode}){
const{currentBatch,selectedIndex}=useWorkstation()
const{activeBrand}=useBrand()
const[state,setState]=useState<QuickEditState>({isGenerating:false,originalPath:null,resultPath:null,prompt:'',error:null})
const mountedRef=useRef(true)
const requestIdRef=useRef<string|null>(null)
const pendingResultRef=useRef<string|null>(null)
//Cleanup on unmount
useEffect(()=>{mountedRef.current=true;return()=>{mountedRef.current=false;if(pendingResultRef.current)bridge.deleteAsset(pendingResultRef.current).catch(()=>{})}},[])
//Reset when selected image changes
const currImg=currentBatch[selectedIndex]
const currPath=currImg?.originalPath||currImg?.path||null
useEffect(()=>{if(state.originalPath&&currPath!==state.originalPath){setState({isGenerating:false,originalPath:null,resultPath:null,prompt:'',error:null});requestIdRef.current=null}},[currPath,state.originalPath])
//Start edit mode for an image
const startEdit=useCallback((path:string)=>{setState(s=>({...s,originalPath:path,resultPath:null,prompt:'',error:null}))},[])
//Submit edit request to bridge
const submitEdit=useCallback(async(prompt:string)=>{
const path=state.originalPath||currPath
if(!path||!activeBrand)return
const reqId=genId()
requestIdRef.current=reqId
setState(s=>({...s,isGenerating:true,prompt,error:null}))
try{
const att={name:'edit-source.png',path,source:'asset'as const}
const res=await bridge.chat(`Edit this image: ${prompt}`,[att],{project_slug:null})
if(!mountedRef.current||requestIdRef.current!==reqId)return
const imgPath=res?.images?.[0]?.path
if(!imgPath){setState(s=>({...s,isGenerating:false,error:'No image generated'}));return}
pendingResultRef.current=imgPath
setState(s=>({...s,isGenerating:false,resultPath:imgPath,originalPath:path}))
}catch(e){
if(!mountedRef.current)return
const msg=e instanceof Error?e.message:'Edit failed'
setState(s=>({...s,isGenerating:false,error:msg}))
}
},[state.originalPath,currPath,activeBrand])
//Cancel pending edit
const cancelEdit=useCallback(()=>{
requestIdRef.current=null
if(pendingResultRef.current){bridge.deleteAsset(pendingResultRef.current).catch(()=>{});pendingResultRef.current=null}
setState({isGenerating:false,originalPath:null,resultPath:null,prompt:'',error:null})
},[])
//Accept result (for later stages)
const acceptResult=useCallback(()=>{pendingResultRef.current=null;setState({isGenerating:false,originalPath:null,resultPath:null,prompt:'',error:null})},[])
//Discard result and delete file
const discardResult=useCallback(async()=>{
if(state.resultPath){try{await bridge.deleteAsset(state.resultPath)}catch(e){console.warn('Delete failed:',e)}}
pendingResultRef.current=null
setState({isGenerating:false,originalPath:null,resultPath:null,prompt:'',error:null})
},[state.resultPath])
//Clear error
const clearError=useCallback(()=>{setState(s=>({...s,error:null}))},[])
return(<QuickEditContext.Provider value={{...state,startEdit,submitEdit,cancelEdit,acceptResult,discardResult,clearError}}>{children}</QuickEditContext.Provider>)
}
export function useQuickEdit(){const ctx=useContext(QuickEditContext);if(!ctx)throw new Error('useQuickEdit must be used within a QuickEditProvider');return ctx}
