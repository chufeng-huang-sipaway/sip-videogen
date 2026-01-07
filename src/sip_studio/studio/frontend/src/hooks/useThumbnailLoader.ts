//Hook for lazy-loading thumbnails with caching and concurrency limiting
import{useState,useCallback,useRef,useEffect}from'react'
//Session-level cache for thumbnails
const thumbnailCache=new Map<string,string>()
//Concurrency control
const MAX_CONCURRENT=4
let activeLoads=0
const queue:Array<()=>void>=[]
function runNext(){if(queue.length>0&&activeLoads<MAX_CONCURRENT){const next=queue.shift();if(next)next()}}
export function clearThumbnailCache(){thumbnailCache.clear()}
export function getCachedThumbnail(path:string):string|undefined{return thumbnailCache.get(path)}
export interface UseThumbnailLoaderOptions{maxConcurrent?:number;rootMargin?:string;onLoadError?:(path:string)=>void}
export interface UseThumbnailLoaderReturn{src:string|null;isLoading:boolean;hasError:boolean;containerRef:React.RefObject<HTMLDivElement|null>;reload:()=>void}
function isNotFoundError(msg:string):boolean{return msg.toLowerCase().includes('not found')}
export function useThumbnailLoader(path:string,loadFn:(path:string)=>Promise<string>,options:UseThumbnailLoaderOptions={}):UseThumbnailLoaderReturn{
const{rootMargin='50px',onLoadError}=options
const[src,setSrc]=useState<string|null>(()=>thumbnailCache.get(path)??null)
const[isLoading,setIsLoading]=useState(!thumbnailCache.has(path))
const[hasError,setHasError]=useState(false)
const containerRef=useRef<HTMLDivElement>(null)
const loadedRef=useRef(false)
const unmountedRef=useRef(false)
const load=useCallback(async()=>{
if(thumbnailCache.has(path)){if(!unmountedRef.current){setSrc(thumbnailCache.get(path)!);setIsLoading(false)};return}
if(activeLoads>=MAX_CONCURRENT){await new Promise<void>(r=>{queue.push(r)})}
activeLoads++
try{const dataUrl=await loadFn(path);thumbnailCache.set(path,dataUrl)
if(!unmountedRef.current){setSrc(dataUrl);setHasError(false)}
}catch(err){const msg=err instanceof Error?err.message:String(err)
if(!unmountedRef.current)setHasError(true)
if(isNotFoundError(msg))onLoadError?.(path)
}finally{if(!unmountedRef.current)setIsLoading(false);activeLoads--;runNext()}
},[path,loadFn,onLoadError])
const reload=useCallback(()=>{thumbnailCache.delete(path);loadedRef.current=false;setHasError(false);setIsLoading(true);void load()},[path,load])
useEffect(()=>{unmountedRef.current=false;return()=>{unmountedRef.current=true}},[])
useEffect(()=>{
if(loadedRef.current||thumbnailCache.has(path)){setIsLoading(false);if(thumbnailCache.has(path))setSrc(thumbnailCache.get(path)!);return}
const container=containerRef.current;if(!container)return
if(typeof IntersectionObserver==='undefined'){loadedRef.current=true;void load();return}
const observer=new IntersectionObserver((entries)=>{
if(entries[0]?.isIntersecting&&!loadedRef.current){loadedRef.current=true;observer.disconnect();void load()}
},{rootMargin})
observer.observe(container)
return()=>observer.disconnect()
},[path,load,rootMargin])
return{src,isLoading,hasError,containerRef,reload}}
