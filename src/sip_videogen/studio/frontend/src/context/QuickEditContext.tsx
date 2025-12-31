/* eslint-disable react-refresh/only-export-components */
import{createContext,useContext,useState,useCallback,useRef,useEffect}from'react'
import type{ReactNode}from'react'
import{bridge}from'../lib/bridge'
import{useWorkstation}from'./WorkstationContext'
import{useBrand}from'./BrandContext'
import{invalidatePath,clearAllCaches}from'../lib/thumbnailCache'
//Generate unique request ID with fallback for older runtimes
const genId=()=>crypto.randomUUID?.()??`${Date.now()}-${Math.random().toString(36).slice(2)}`
//Quick edit state interface
interface QuickEditState{isGenerating:boolean;originalPath:string|null;resultPath:string|null;prompt:string;error:string|null;isActionLoading:boolean}
interface QuickEditContextType extends QuickEditState{startEdit:(path:string)=>void;submitEdit:(prompt:string)=>Promise<void>;cancelEdit:()=>void;keepAndOverride:()=>Promise<{success:boolean;newPath?:string;error?:string}>;saveAsCopy:()=>void;rerun:()=>void;discardResult:()=>Promise<void>;clearError:()=>void}
const QuickEditContext=createContext<QuickEditContextType|null>(null)
export function QuickEditProvider({children}:{children:ReactNode}){
const{currentBatch,selectedIndex,bumpStatusVersion,prependToBatch}=useWorkstation()
const{activeBrand}=useBrand()
const[state,setState]=useState<QuickEditState>({isGenerating:false,originalPath:null,resultPath:null,prompt:'',error:null,isActionLoading:false})
const mountedRef=useRef(true)
const requestIdRef=useRef<string|null>(null)
const pendingResultRef=useRef<string|null>(null)
//Cleanup on unmount
useEffect(()=>{mountedRef.current=true;return()=>{mountedRef.current=false;if(pendingResultRef.current)bridge.deleteAsset(pendingResultRef.current).catch(()=>{})}},[])
//Reset when selected image changes
const currImg=currentBatch[selectedIndex]
const currPath=currImg?.originalPath||currImg?.path||null
useEffect(()=>{if(state.originalPath&&currPath!==state.originalPath){setState({isGenerating:false,originalPath:null,resultPath:null,prompt:'',error:null,isActionLoading:false});requestIdRef.current=null}},[currPath,state.originalPath])
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
//Load metadata to get original product references for re-attachment
const meta=await bridge.getImageMetadata(path)
const raw=meta?.product_slugs
const prods:string[]=Array.isArray(raw)?[...new Set(raw.filter((s):s is string=>typeof s==='string'&&s.trim()!==''))]:[]
console.log('[QuickEdit] path=',path,'meta=',meta,'raw=',raw,'prods=',prods)
const res=await bridge.chat(`Edit this image: ${prompt}`,[att],{project_slug:null,attached_products:prods.length>0?prods:undefined})
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
setState({isGenerating:false,originalPath:null,resultPath:null,prompt:'',error:null,isActionLoading:false})
},[])
//Keep & Override: backup-first replace original with result
const keepAndOverride=useCallback(async():Promise<{success:boolean;newPath?:string;error?:string}>=>{
if(!state.originalPath||!state.resultPath)return{success:false,error:'No paths'}
setState(s=>({...s,isActionLoading:true}))
try{
const origPath=state.originalPath
const newPath=await bridge.replaceAsset(origPath,state.resultPath)
pendingResultRef.current=null
//Invalidate cache for old path so ImageDisplay reloads fresh
invalidatePath(origPath)
if(newPath&&newPath!==origPath)invalidatePath(newPath)
//Clear all caches to ensure fresh reload (path may have changed extension)
clearAllCaches()
setState({isGenerating:false,originalPath:null,resultPath:null,prompt:'',error:null,isActionLoading:false})
bumpStatusVersion()
return{success:true,newPath}
}catch(e){
const msg=e instanceof Error?e.message:'Replace failed'
setState(s=>({...s,isActionLoading:false,error:msg}))
return{success:false,error:msg}
}
},[state.originalPath,state.resultPath,bumpStatusVersion])
//Save as Copy: dismiss preview, result persists in generated folder, add to batch
const saveAsCopy=useCallback(()=>{
if(state.resultPath){
const newImg={id:genId(),path:state.resultPath,prompt:state.prompt,timestamp:new Date().toISOString()}
prependToBatch([newImg])
}
pendingResultRef.current=null
setState({isGenerating:false,originalPath:null,resultPath:null,prompt:'',error:null,isActionLoading:false})
bumpStatusVersion()
},[state.resultPath,state.prompt,prependToBatch,bumpStatusVersion])
//Rerun: delete current result, reopen popover with same prompt
const rerun=useCallback(()=>{
const savedPrompt=state.prompt
if(state.resultPath){bridge.deleteAsset(state.resultPath).catch(()=>{})}
pendingResultRef.current=null
setState(s=>({...s,resultPath:null,prompt:savedPrompt,error:null,isActionLoading:false}))
},[state.prompt,state.resultPath])
//Discard result and delete file
const discardResult=useCallback(async()=>{
if(state.resultPath){try{await bridge.deleteAsset(state.resultPath)}catch(e){console.warn('Delete failed:',e)}}
pendingResultRef.current=null
setState({isGenerating:false,originalPath:null,resultPath:null,prompt:'',error:null,isActionLoading:false})
},[state.resultPath])
//Clear error
const clearError=useCallback(()=>{setState(s=>({...s,error:null}))},[])
return(<QuickEditContext.Provider value={{...state,startEdit,submitEdit,cancelEdit,keepAndOverride,saveAsCopy,rerun,discardResult,clearError}}>{children}</QuickEditContext.Provider>)
}
export function useQuickEdit(){const ctx=useContext(QuickEditContext);if(!ctx)throw new Error('useQuickEdit must be used within a QuickEditProvider');return ctx}
