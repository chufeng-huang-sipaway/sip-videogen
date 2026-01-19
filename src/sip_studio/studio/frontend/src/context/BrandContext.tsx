/* eslint-disable react-refresh/only-export-components */
import{createContext,useContext,useState,useEffect,useCallback,useRef}from'react'
import type{ReactNode}from'react'
import{bridge,waitForPyWebViewReady}from'@/lib/bridge'
import type{BrandEntry,BrandCreationJob}from'@/lib/bridge'
import type{BrandIdentityFull,IdentitySection,SectionDataMap}from'@/types/brand-identity'
import{toast}from'@/components/ui/toaster'
interface BrandContextType{brands:BrandEntry[];activeBrand:string|null;isLoading:boolean;error:string|null;selectBrand:(slug:string)=>Promise<void>;refresh:()=>Promise<void>;identity:BrandIdentityFull|null;isIdentityLoading:boolean;identityError:string|null;refreshIdentity:()=>Promise<void>;setIdentity:(identity:BrandIdentityFull|null)=>void;updateIdentitySection:<S extends IdentitySection>(section:S,data:SectionDataMap[S])=>Promise<BrandIdentityFull>;refreshAdvisorContext:()=>Promise<{success:boolean;message?:string;error?:string}>;creatingBrand:BrandCreationJob|null;checkBrandCreationJob:()=>Promise<void>;clearBrandCreationJob:()=>Promise<void>;startBrandCreation:(name:string,url:string)=>Promise<{slug:string}>}
const BrandContext=createContext<BrandContextType|null>(null)
const POLL_INTERVAL=5000
export function BrandProvider({children}:{children:ReactNode}){
const[brands,setBrands]=useState<BrandEntry[]>([])
const[activeBrand,setActiveBrand]=useState<string|null>(null)
const[isLoading,setIsLoading]=useState(true)
const[error,setError]=useState<string|null>(null)
//Identity state
const[identity,setIdentityState]=useState<BrandIdentityFull|null>(null)
const[isIdentityLoading,setIsIdentityLoading]=useState(false)
const[identityError,setIdentityError]=useState<string|null>(null)
//Brand creation job state
const[creatingBrand,setCreatingBrand]=useState<BrandCreationJob|null>(null)
const pollRef=useRef<number|null>(null)
const applyIdentity=useCallback((next:BrandIdentityFull|null)=>{setIdentityState(next);if(next){setBrands(prev=>prev.map(brand=>brand.slug===next.slug?{...brand,name:next.core.name}:brand))}},[])
const refresh=useCallback(async()=>{setIsLoading(true);setError(null)
try{const ready=await waitForPyWebViewReady()
if(!ready){setBrands([{slug:'summit-coffee',name:'Summit Coffee',category:'Coffee'},{slug:'acme-corp',name:'Acme Corp',category:'Technology'}]);setActiveBrand('summit-coffee');return}
const result=await bridge.getBrands();setBrands(result.brands);setActiveBrand(result.active)
}catch(err){setError(err instanceof Error?err.message:'Failed to load brands')
}finally{setIsLoading(false)}},[])
//Fetch identity for active brand
const refreshIdentity=useCallback(async()=>{const ready=await waitForPyWebViewReady()
if(!ready){applyIdentity(null);return}
setIsIdentityLoading(true);setIdentityError(null)
try{const result=await bridge.getBrandIdentity();applyIdentity(result)
}catch(err){setIdentityError(err instanceof Error?err.message:'Failed to load brand identity');applyIdentity(null)
}finally{setIsIdentityLoading(false)}},[applyIdentity])
const selectBrand=useCallback(async(slug:string)=>{setError(null);applyIdentity(null);setIdentityError(null)
try{const ready=await waitForPyWebViewReady();if(ready){await bridge.setBrand(slug);await bridge.backfillImages(slug).catch(()=>{})}setActiveBrand(slug)
}catch(err){setError(err instanceof Error?err.message:'Failed to select brand')}},[applyIdentity])
//Refresh AI advisor context
const refreshAdvisorContext=useCallback(async()=>{
try{const ready=await waitForPyWebViewReady();if(!ready)return{success:false,error:'Not running in PyWebView'}
const result=await bridge.refreshBrandMemory();return{success:true,message:result.message}
}catch(err){return{success:false,error:err instanceof Error?err.message:'Failed to refresh AI context'}}},[])
//Update identity section and auto-refresh advisor context
const updateIdentitySection=useCallback(async<S extends IdentitySection>(section:S,data:SectionDataMap[S]):Promise<BrandIdentityFull>=>{
const updated=await bridge.updateBrandIdentitySection(section,data)
applyIdentity(updated)
//Auto-refresh AI advisor context after identity changes
await refreshAdvisorContext()
return updated
},[refreshAdvisorContext,applyIdentity])
//Brand creation job polling
const checkBrandCreationJob=useCallback(async()=>{
try{const ready=await waitForPyWebViewReady();if(!ready)return
const job=await bridge.getBrandCreationJob()
if(!job){setCreatingBrand(null);return}
setCreatingBrand(job)
//Handle completion
if(job.status==='completed'){setCreatingBrand(null);toast.success(`Brand "${job.brand_name}" created successfully!`);await refresh();await selectBrand(job.slug);await bridge.clearBrandCreationJob().catch(()=>{})}
//Handle failure
else if(job.status==='failed'){toast.error(job.error||'Brand creation failed')}
//Handle cancellation
else if(job.status==='cancelled'){toast.info('Brand creation was cancelled')}
}catch(err){console.warn('[BrandContext] Failed to check brand creation job:',err)}},[refresh,selectBrand])
//Clear failed/cancelled job
const clearBrandCreationJob=useCallback(async()=>{
try{const ready=await waitForPyWebViewReady();if(!ready)return
await bridge.clearBrandCreationJob();setCreatingBrand(null)
}catch(err){console.warn('[BrandContext] Failed to clear brand creation job:',err)}},[])
//Start brand creation from website - immediately triggers polling
const startBrandCreation=useCallback(async(name:string,url:string)=>{
const result=await bridge.createBrandFromWebsite(name,url)
await checkBrandCreationJob()//Sets creatingBrand, triggers polling
return result},[checkBrandCreationJob])
//Poll for brand creation job on startup and periodically
useEffect(()=>{checkBrandCreationJob()},[checkBrandCreationJob])
useEffect(()=>{
//Only poll if we have an active job in running/pending state
if(!creatingBrand||creatingBrand.status==='completed'||creatingBrand.status==='failed'||creatingBrand.status==='cancelled')return
pollRef.current=window.setInterval(()=>{checkBrandCreationJob()},POLL_INTERVAL)
return()=>{if(pollRef.current){clearInterval(pollRef.current);pollRef.current=null}}},[creatingBrand,checkBrandCreationJob])
useEffect(()=>{applyIdentity(null);setIdentityError(null)},[activeBrand,applyIdentity])
useEffect(()=>{refresh()},[refresh])
return(<BrandContext.Provider value={{brands,activeBrand,isLoading,error,selectBrand,refresh,identity,isIdentityLoading,identityError,refreshIdentity,setIdentity:applyIdentity,updateIdentitySection,refreshAdvisorContext,creatingBrand,checkBrandCreationJob,clearBrandCreationJob,startBrandCreation}}>{children}</BrandContext.Provider>)}
export function useBrand(){const context=useContext(BrandContext);if(!context)throw new Error('useBrand must be used within a BrandProvider');return context}
