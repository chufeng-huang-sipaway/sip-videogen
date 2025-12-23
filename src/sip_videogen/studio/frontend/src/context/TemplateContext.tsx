/* eslint-disable react-refresh/only-export-components */
import {createContext,useContext,useState,useEffect,useCallback,type ReactNode} from 'react'
import {bridge,waitForPyWebViewReady,type TemplateSummary,type TemplateFull,type AttachedTemplate} from '@/lib/bridge'
import {useBrand} from './BrandContext'
export interface CreateTemplateInput {
name:string
description:string
images?:Array<{filename:string;data:string}>
defaultStrict?:boolean
}
interface TemplateContextType {
templates:TemplateSummary[]
attachedTemplates:AttachedTemplate[]
isLoading:boolean
error:string|null
refresh:()=>Promise<void>
attachTemplate:(slug:string,strict?:boolean)=>void
detachTemplate:(slug:string)=>void
setTemplateStrictness:(slug:string,strict:boolean)=>void
clearTemplateAttachments:()=>void
createTemplate:(data:CreateTemplateInput)=>Promise<string>
updateTemplate:(templateSlug:string,name?:string,description?:string,defaultStrict?:boolean)=>Promise<void>
deleteTemplate:(slug:string)=>Promise<void>
getTemplate:(slug:string)=>Promise<TemplateFull>
getTemplateImages:(slug:string)=>Promise<string[]>
uploadTemplateImage:(slug:string,filename:string,dataBase64:string)=>Promise<string>
deleteTemplateImage:(slug:string,filename:string)=>Promise<void>
setPrimaryTemplateImage:(slug:string,filename:string)=>Promise<void>
}
const TemplateContext=createContext<TemplateContextType|null>(null)
export function TemplateProvider({children}:{children:ReactNode}){
const {activeBrand}=useBrand()
const [templates,setTemplates]=useState<TemplateSummary[]>([])
const [attachedTemplates,setAttachedTemplates]=useState<AttachedTemplate[]>([])
const [isLoading,setIsLoading]=useState(false)
const [error,setError]=useState<string|null>(null)
const refresh=useCallback(async()=>{
if(!activeBrand){setTemplates([]);return}
setIsLoading(true)
setError(null)
try{
const ready=await waitForPyWebViewReady()
if(!ready){
//Mock data for dev
setTemplates([{slug:'hero-banner',name:'Hero Banner',description:'Full-width hero banner layout',primary_image:'templates/hero-banner/images/main.png',default_strict:true,created_at:new Date().toISOString(),updated_at:new Date().toISOString()}])
return}
const result=await bridge.getTemplates()
setTemplates(result)
}catch(err){setError(err instanceof Error?err.message:'Failed to load templates')
}finally{setIsLoading(false)}},[activeBrand])
//Refresh when brand changes
useEffect(()=>{refresh();setAttachedTemplates([])},[refresh])
const attachTemplate=useCallback((slug:string,strict?:boolean)=>{
setAttachedTemplates(prev=>{
if(prev.some(t=>t.template_slug===slug))return prev
//Find template to get default_strict
const template=templates.find(t=>t.slug===slug)
const useStrict=strict!==undefined?strict:template?.default_strict??true
return[...prev,{template_slug:slug,strict:useStrict}]})},[templates])
const detachTemplate=useCallback((slug:string)=>{
setAttachedTemplates(prev=>prev.filter(t=>t.template_slug!==slug))},[])
const setTemplateStrictness=useCallback((slug:string,strict:boolean)=>{
setAttachedTemplates(prev=>prev.map(t=>t.template_slug===slug?{...t,strict}:t))},[])
const clearTemplateAttachments=useCallback(()=>{setAttachedTemplates([])},[])
const createTemplate=useCallback(async(data:CreateTemplateInput):Promise<string>=>{
const ready=await waitForPyWebViewReady()
if(!ready)throw new Error('Not running in PyWebView')
const slug=await bridge.createTemplate(data.name,data.description,data.images,data.defaultStrict)
await refresh()
return slug},[refresh])
const updateTemplate=useCallback(async(templateSlug:string,name?:string,description?:string,defaultStrict?:boolean):Promise<void>=>{
const ready=await waitForPyWebViewReady()
if(!ready)throw new Error('Not running in PyWebView')
await bridge.updateTemplate(templateSlug,name,description,defaultStrict)
await refresh()},[refresh])
const deleteTemplate=useCallback(async(slug:string):Promise<void>=>{
const ready=await waitForPyWebViewReady()
if(!ready)throw new Error('Not running in PyWebView')
await bridge.deleteTemplate(slug)
//Remove from attachments if attached
setAttachedTemplates(prev=>prev.filter(t=>t.template_slug!==slug))
await refresh()},[refresh])
const getTemplate=useCallback(async(slug:string):Promise<TemplateFull>=>{
const ready=await waitForPyWebViewReady()
if(!ready)throw new Error('Not running in PyWebView')
return bridge.getTemplate(slug)},[])
const getTemplateImages=useCallback(async(slug:string):Promise<string[]>=>{
const ready=await waitForPyWebViewReady()
if(!ready)throw new Error('Not running in PyWebView')
return bridge.getTemplateImages(slug)},[])
const uploadTemplateImage=useCallback(async(slug:string,filename:string,dataBase64:string):Promise<string>=>{
const ready=await waitForPyWebViewReady()
if(!ready)throw new Error('Not running in PyWebView')
const path=await bridge.uploadTemplateImage(slug,filename,dataBase64)
await refresh()
return path},[refresh])
const deleteTemplateImage=useCallback(async(slug:string,filename:string):Promise<void>=>{
const ready=await waitForPyWebViewReady()
if(!ready)throw new Error('Not running in PyWebView')
await bridge.deleteTemplateImage(slug,filename)
await refresh()},[refresh])
const setPrimaryTemplateImage=useCallback(async(slug:string,filename:string):Promise<void>=>{
const ready=await waitForPyWebViewReady()
if(!ready)throw new Error('Not running in PyWebView')
await bridge.setPrimaryTemplateImage(slug,filename)
await refresh()},[refresh])
return(
<TemplateContext.Provider value={{templates,attachedTemplates,isLoading,error,refresh,attachTemplate,detachTemplate,setTemplateStrictness,clearTemplateAttachments,createTemplate,updateTemplate,deleteTemplate,getTemplate,getTemplateImages,uploadTemplateImage,deleteTemplateImage,setPrimaryTemplateImage}}>
{children}
</TemplateContext.Provider>)}
export function useTemplates(){
const context=useContext(TemplateContext)
if(!context)throw new Error('useTemplates must be used within a TemplateProvider')
return context}
