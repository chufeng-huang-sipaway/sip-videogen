/* eslint-disable react-refresh/only-export-components */
import {createContext,useContext,useState,useEffect,useCallback,type ReactNode} from 'react'
import {bridge,waitForPyWebViewReady,type StyleReferenceSummary,type StyleReferenceFull,type AttachedStyleReference,type StyleReferenceAnalysis} from '@/lib/bridge'
import {useBrand} from './BrandContext'
export interface CreateStyleReferenceInput {
name:string
description:string
images?:Array<{filename:string;data:string}>
defaultStrict?:boolean
}
interface StyleReferenceContextType {
styleReferences:StyleReferenceSummary[]
attachedStyleReferences:AttachedStyleReference[]
isLoading:boolean
error:string|null
refresh:()=>Promise<void>
attachStyleReference:(slug:string,strict?:boolean)=>void
detachStyleReference:(slug:string)=>void
setStyleReferenceStrictness:(slug:string,strict:boolean)=>void
clearStyleReferenceAttachments:()=>void
createStyleReference:(data:CreateStyleReferenceInput)=>Promise<string>
updateStyleReference:(styleRefSlug:string,name?:string,description?:string,defaultStrict?:boolean)=>Promise<void>
deleteStyleReference:(slug:string)=>Promise<void>
getStyleReference:(slug:string)=>Promise<StyleReferenceFull>
getStyleReferenceImages:(slug:string)=>Promise<string[]>
uploadStyleReferenceImage:(slug:string,filename:string,dataBase64:string)=>Promise<string>
deleteStyleReferenceImage:(slug:string,filename:string)=>Promise<void>
setPrimaryStyleReferenceImage:(slug:string,filename:string)=>Promise<void>
reanalyzeStyleReference:(slug:string)=>Promise<StyleReferenceAnalysis>
}
const StyleReferenceContext=createContext<StyleReferenceContextType|null>(null)
export function StyleReferenceProvider({children}:{children:ReactNode}){
const {activeBrand}=useBrand()
const [styleReferences,setStyleReferences]=useState<StyleReferenceSummary[]>([])
const [attachedStyleReferences,setAttachedStyleReferences]=useState<AttachedStyleReference[]>([])
const [isLoading,setIsLoading]=useState(false)
const [error,setError]=useState<string|null>(null)
const refresh=useCallback(async()=>{
if(!activeBrand){setStyleReferences([]);return}
setIsLoading(true)
setError(null)
try{
const ready=await waitForPyWebViewReady()
if(!ready){
//Mock data for dev
setStyleReferences([{slug:'hero-banner',name:'Hero Banner',description:'Full-width hero banner layout',primary_image:'style_references/hero-banner/images/main.png',default_strict:true,created_at:new Date().toISOString(),updated_at:new Date().toISOString()}])
return}
const result=await bridge.getStyleReferences()
setStyleReferences(result)
}catch(err){setError(err instanceof Error?err.message:'Failed to load style references')
}finally{setIsLoading(false)}},[activeBrand])
//Refresh when brand changes
useEffect(()=>{refresh();setAttachedStyleReferences([])},[refresh])
const attachStyleReference=useCallback((slug:string,strict?:boolean)=>{
setAttachedStyleReferences(prev=>{
if(prev.some(t=>t.style_reference_slug===slug))return prev
//Find style reference to get default_strict
const sr=styleReferences.find(t=>t.slug===slug)
const useStrict=strict!==undefined?strict:sr?.default_strict??true
return[...prev,{style_reference_slug:slug,strict:useStrict}]})},[styleReferences])
const detachStyleReference=useCallback((slug:string)=>{
setAttachedStyleReferences(prev=>prev.filter(t=>t.style_reference_slug!==slug))},[])
const setStyleReferenceStrictness=useCallback((slug:string,strict:boolean)=>{
setAttachedStyleReferences(prev=>prev.map(t=>t.style_reference_slug===slug?{...t,strict}:t))},[])
const clearStyleReferenceAttachments=useCallback(()=>{setAttachedStyleReferences([])},[])
const createStyleReference=useCallback(async(data:CreateStyleReferenceInput):Promise<string>=>{
const ready=await waitForPyWebViewReady()
if(!ready)throw new Error('Not running in PyWebView')
const slug=await bridge.createStyleReference(data.name,data.description,data.images,data.defaultStrict)
await refresh()
return slug},[refresh])
const updateStyleReference=useCallback(async(styleRefSlug:string,name?:string,description?:string,defaultStrict?:boolean):Promise<void>=>{
const ready=await waitForPyWebViewReady()
if(!ready)throw new Error('Not running in PyWebView')
await bridge.updateStyleReference(styleRefSlug,name,description,defaultStrict)
await refresh()},[refresh])
const deleteStyleReference=useCallback(async(slug:string):Promise<void>=>{
const ready=await waitForPyWebViewReady()
if(!ready)throw new Error('Not running in PyWebView')
await bridge.deleteStyleReference(slug)
//Remove from attachments if attached
setAttachedStyleReferences(prev=>prev.filter(t=>t.style_reference_slug!==slug))
await refresh()},[refresh])
const getStyleReference=useCallback(async(slug:string):Promise<StyleReferenceFull>=>{
const ready=await waitForPyWebViewReady()
if(!ready)throw new Error('Not running in PyWebView')
return bridge.getStyleReference(slug)},[])
const getStyleReferenceImages=useCallback(async(slug:string):Promise<string[]>=>{
const ready=await waitForPyWebViewReady()
if(!ready)throw new Error('Not running in PyWebView')
return bridge.getStyleReferenceImages(slug)},[])
const uploadStyleReferenceImage=useCallback(async(slug:string,filename:string,dataBase64:string):Promise<string>=>{
const ready=await waitForPyWebViewReady()
if(!ready)throw new Error('Not running in PyWebView')
const path=await bridge.uploadStyleReferenceImage(slug,filename,dataBase64)
await refresh()
return path},[refresh])
const deleteStyleReferenceImage=useCallback(async(slug:string,filename:string):Promise<void>=>{
const ready=await waitForPyWebViewReady()
if(!ready)throw new Error('Not running in PyWebView')
await bridge.deleteStyleReferenceImage(slug,filename)
await refresh()},[refresh])
const setPrimaryStyleReferenceImage=useCallback(async(slug:string,filename:string):Promise<void>=>{
const ready=await waitForPyWebViewReady()
if(!ready)throw new Error('Not running in PyWebView')
await bridge.setPrimaryStyleReferenceImage(slug,filename)
await refresh()},[refresh])
const reanalyzeStyleReference=useCallback(async(slug:string):Promise<StyleReferenceAnalysis>=>{
const ready=await waitForPyWebViewReady()
if(!ready)throw new Error('Not running in PyWebView')
const analysis=await bridge.reanalyzeStyleReference(slug)
await refresh()
return analysis},[refresh])
return(
<StyleReferenceContext.Provider value={{styleReferences,attachedStyleReferences,isLoading,error,refresh,attachStyleReference,detachStyleReference,setStyleReferenceStrictness,clearStyleReferenceAttachments,createStyleReference,updateStyleReference,deleteStyleReference,getStyleReference,getStyleReferenceImages,uploadStyleReferenceImage,deleteStyleReferenceImage,setPrimaryStyleReferenceImage,reanalyzeStyleReference}}>
{children}
</StyleReferenceContext.Provider>)}
export function useStyleReferences(){
const context=useContext(StyleReferenceContext)
if(!context)throw new Error('useStyleReferences must be used within a StyleReferenceProvider')
return context}
