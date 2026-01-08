//useQuickGenerator - manages quick generate state and actions
import{useState,useEffect,useCallback}from'react'
import{bridge,isPyWebView,type SessionState}from'@/lib/bridge'
import{eventBus,EVENT_NAMES}from'@/lib/eventBus'
import type{QuickGenerateProgress,QuickGenerateResult,QuickGenerateStatus}from'@/types/quickGenerate'
import{getQuickGenerateStatus}from'@/types/quickGenerate'
export interface GeneratedImageEntry{
path:string
prompt:string
error?:string}
export interface UseQuickGeneratorResult{
//State
status:QuickGenerateStatus
progress:QuickGenerateProgress|null
result:QuickGenerateResult|null
generatedImages:GeneratedImageEntry[]
errors:string[]
isOpen:boolean
//Actions
open:()=>void
close:()=>void
generate:(prompts:string[],aspectRatio?:string,productSlug?:string,styleReferenceSlug?:string,strict?:boolean)=>Promise<void>
cancel:()=>Promise<void>
clear:()=>void
downloadAll:()=>Promise<void>}
export function useQuickGenerator():UseQuickGeneratorResult{
const[isOpen,setIsOpen]=useState(false)
const[progress,setProgress]=useState<QuickGenerateProgress|null>(null)
const[result,setResult]=useState<QuickGenerateResult|null>(null)
const[generatedImages,setGeneratedImages]=useState<GeneratedImageEntry[]>([])
const[errors,setErrors]=useState<string[]>([])
const[runId,setRunId]=useState<string|null>(null)
//Hydrate on mount (check if quick gen job is active)
useEffect(()=>{
if(!isPyWebView())return
bridge.getSessionState().then((state:SessionState)=>{
if(state.activeJob?.jobType==='quick_generate'){
setRunId(state.activeJob.runId)
setIsOpen(true)
//Fetch current progress
bridge.getQuickGenerateProgress().then((p)=>{
if(p)setProgress(p)}).catch(()=>{})}}).catch(()=>{})
},[])
//Subscribe to quick generate events
useEffect(()=>{
const unsubs:Array<()=>void>=[]
//Progress updates
unsubs.push(eventBus.subscribe<QuickGenerateProgress>(EVENT_NAMES.onQuickGenerateProgress,(data)=>{
if(runId&&data.runId!==runId)return
setProgress(data)
//Update generated images from progress
const imgs=data.generatedPaths.map((path,i)=>({path,prompt:i<data.completed?data.currentPrompt:''}))
setGeneratedImages(imgs)
setErrors(data.errors)}))
//Result (job completed)
unsubs.push(eventBus.subscribe<QuickGenerateResult>(EVENT_NAMES.onQuickGenerateResult,(data)=>{
if(runId&&data.runId!==runId)return
setResult(data)
setProgress(null)
//Final images
const imgs=data.generatedPaths.map((path)=>({path,prompt:''}))
setGeneratedImages(imgs)
setErrors(data.errors)
setRunId(null)}))
//Error event
unsubs.push(eventBus.subscribe<{runId:string;error:string}>(EVENT_NAMES.onQuickGenerateError,(data)=>{
if(runId&&data.runId!==runId)return
setErrors(prev=>[...prev,data.error])
setProgress(null)
setResult({runId:data.runId,generatedPaths:[],errors:[data.error],total:0,completed:0,cancelled:false,error:data.error})
setRunId(null)}))
return()=>unsubs.forEach(u=>u())
},[runId])
const open=useCallback(()=>setIsOpen(true),[])
const close=useCallback(()=>setIsOpen(false),[])
const generate=useCallback(async(prompts:string[],aspectRatio?:string,productSlug?:string,styleReferenceSlug?:string,strict?:boolean)=>{
if(!isPyWebView())return
//Clear previous state
setProgress(null)
setResult(null)
setGeneratedImages([])
setErrors([])
const resp=await bridge.quickGenerate(prompts,aspectRatio,productSlug,styleReferenceSlug,strict)
if(resp.started){setRunId(resp.runId);setProgress({total:prompts.length,completed:0,currentPrompt:prompts[0]||'',generatedPaths:[],errors:[],runId:resp.runId})}
},[])
const cancel=useCallback(async()=>{
if(!isPyWebView())return
await bridge.cancelQuickGenerate()
setRunId(null)
},[])
const clear=useCallback(()=>{
setProgress(null)
setResult(null)
setGeneratedImages([])
setErrors([])
setRunId(null)
},[])
const downloadAll=useCallback(async()=>{
if(!isPyWebView()||generatedImages.length===0)return
const paths=generatedImages.map(i=>i.path)
const zipPath=await bridge.downloadImagesAsZip(paths)
//Open the zip file in Finder
if(zipPath){await bridge.openAssetInFinder(zipPath)}
},[generatedImages])
const status=getQuickGenerateStatus(progress,result)
return{status,progress,result,generatedImages,errors,isOpen,open,close,generate,cancel,clear,downloadAll}
}
