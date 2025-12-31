import{useState,useEffect,useCallback,useRef}from'react'
import{bridge,type Inspiration}from'@/lib/bridge'
interface UseInspirationsResult{
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
const VIEWED_STORAGE_KEY='sip-studio-viewed-inspirations'
function loadViewedIds():Set<string>{
try{const stored=localStorage.getItem(VIEWED_STORAGE_KEY);if(stored)return new Set(JSON.parse(stored))}catch{}
return new Set()
}
function saveViewedIds(ids:Set<string>){
try{localStorage.setItem(VIEWED_STORAGE_KEY,JSON.stringify([...ids]))}catch{}
}
export function useInspirations(brandSlug:string|null):UseInspirationsResult{
const[inspirations,setInspirations]=useState<Inspiration[]>([])
const[isGenerating,setIsGenerating]=useState(false)
const[jobId,setJobId]=useState<string|null>(null)
const[progress,setProgress]=useState(0)
const[error,setError]=useState<string|null>(null)
const[viewedIds,setViewedIds]=useState<Set<string>>(loadViewedIds)
const pollTimeoutRef=useRef<number|null>(null)
const pollDelayRef=useRef(1000)
//Ref to track current isGenerating state for setTimeout closure
const isGeneratingRef=useRef(false)
isGeneratingRef.current=isGenerating
//Computed: count of new (unviewed, ready) inspirations
const newCount=inspirations.filter(i=>!viewedIds.has(i.id)&&i.status==='ready').length
//Refresh inspirations from backend
const refresh=useCallback(async()=>{
if(!brandSlug)return
try{
const data=await bridge.getInspirations(brandSlug)
setInspirations(data.inspirations||[])
//If there's an active job, track it
if(data.job&&data.job.status==='generating'){setJobId(data.job.id);setIsGenerating(true);setProgress(data.job.progress)}
else{setIsGenerating(false);setProgress(0)}
setError(null)
}catch(e){setError(e instanceof Error?e.message:'Failed to load inspirations')}
},[brandSlug])
//Poll for job progress
useEffect(()=>{
if(!jobId||!isGenerating)return
const poll=async()=>{
try{
const job=await bridge.getInspirationProgress(jobId)
setProgress(job.progress)
if(job.status==='completed'||job.status==='failed'||job.status==='cancelled'){
setIsGenerating(false);setJobId(null)
if(job.status==='failed')setError(job.error||'Generation failed')
await refresh()
return
}
//Backoff: increase delay up to 5s
pollDelayRef.current=Math.min(pollDelayRef.current+1000,5000)
pollTimeoutRef.current=window.setTimeout(poll,pollDelayRef.current)
}catch(e){
console.error('Polling error:',e)
pollDelayRef.current=Math.min(pollDelayRef.current+1000,5000)
pollTimeoutRef.current=window.setTimeout(poll,pollDelayRef.current)
}
}
pollDelayRef.current=1000
poll()
return()=>{if(pollTimeoutRef.current)clearTimeout(pollTimeoutRef.current)}
},[jobId,isGenerating,refresh])
//Trigger new generation
const triggerGeneration=useCallback(async()=>{
if(!brandSlug||isGenerating)return
setIsGenerating(true);setError(null);setProgress(0)
try{
const newJobId=await bridge.triggerInspirationGeneration(brandSlug)
setJobId(newJobId)
pollDelayRef.current=1000
}catch(e){setIsGenerating(false);setError(e instanceof Error?e.message:'Failed to start generation')}
},[brandSlug,isGenerating])
//Save an inspiration image
const save=useCallback(async(inspirationId:string,imageIdx:number,projectSlug?:string|null)=>{
try{
const result=await bridge.saveInspirationImage(inspirationId,imageIdx,projectSlug)
if(!result.success)throw new Error(result.error||'Save failed')
await refresh()
}catch(e){console.error('Save error:',e);throw e}
},[refresh])
//Dismiss an inspiration
const dismiss=useCallback(async(inspirationId:string)=>{
try{await bridge.dismissInspiration(inspirationId);await refresh()}
catch(e){console.error('Dismiss error:',e);throw e}
},[refresh])
//Request more like this
const moreLikeThis=useCallback(async(inspirationId:string)=>{
if(!brandSlug||isGenerating)return
setIsGenerating(true);setError(null);setProgress(0)
try{
const newJobId=await bridge.requestMoreLike(inspirationId)
setJobId(newJobId)
pollDelayRef.current=1000
}catch(e){setIsGenerating(false);setError(e instanceof Error?e.message:'Failed to request more like this')}
},[brandSlug,isGenerating])
//Mark inspiration as viewed
const markViewed=useCallback((inspirationId:string)=>{
setViewedIds(prev=>{const next=new Set(prev);next.add(inspirationId);saveViewedIds(next);return next})
},[])
//Cancel current job
const cancelCurrentJob=useCallback(async()=>{
if(!jobId)return
try{await bridge.cancelInspirationJob(jobId);setIsGenerating(false);setJobId(null);setProgress(0)}
catch(e){console.error('Cancel error:',e)}
},[jobId])
//Track previous brand slug for brand switch detection
const prevBrandRef=useRef<string|null>(null)
const hasInitialized=useRef(false)
//Handle brand switch: cancel pending job, load cached, auto-trigger generation
useEffect(()=>{
if(!brandSlug)return
const prevBrand=prevBrandRef.current
const isBrandSwitch=prevBrand&&prevBrand!==brandSlug
prevBrandRef.current=brandSlug
const handleBrandChange=async()=>{
//If brand changed, cancel any jobs for the OLD brand
if(isBrandSwitch){
try{await bridge.cancelInspirationJobsForBrand(prevBrand)}catch{}
setIsGenerating(false);setJobId(null);setProgress(0)
}
//Load cached inspirations first
await refresh()
//Auto-trigger generation on initial load OR brand switch (if not already generating)
if(!hasInitialized.current||isBrandSwitch){
hasInitialized.current=true
//Small delay to let UI settle before triggering background work
setTimeout(async()=>{
if(!isGeneratingRef.current){
try{await triggerGeneration()}catch(e){console.error('Auto-trigger error:',e)}
}
},500)
}
}
handleBrandChange()
// eslint-disable-next-line react-hooks/exhaustive-deps
},[brandSlug])
return{inspirations,isGenerating,jobId,progress,error,newCount,viewedIds,triggerGeneration,save,dismiss,moreLikeThis,markViewed,refresh,cancelCurrentJob}
}
