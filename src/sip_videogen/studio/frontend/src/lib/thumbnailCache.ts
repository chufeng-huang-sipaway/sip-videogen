//Centralized thumbnail cache with concurrency control
const cache=new Map<string,string>()
const fullCache=new Map<string,string>()
const MAX_CONCURRENT=4
let activeLoads=0
const queue:Array<()=>void>=[]
function runNext(){if(queue.length>0&&activeLoads<MAX_CONCURRENT){const next=queue.shift();if(next)next()}}
//Thumbnail cache
export function getThumbCached(path:string):string|undefined{return cache.get(path)}
export function setThumbCached(path:string,dataUrl:string):void{cache.set(path,dataUrl)}
export function hasThumbCached(path:string):boolean{return cache.has(path)}
//Full image cache
export function getFullCached(path:string):string|undefined{return fullCache.get(path)}
export function setFullCached(path:string,dataUrl:string):void{fullCache.set(path,dataUrl)}
export function hasFullCached(path:string):boolean{return fullCache.has(path)}
//Invalidate specific path (both caches)
export function invalidatePath(path:string):void{cache.delete(path);fullCache.delete(path)}
//Clear all caches
export function clearAllCaches():void{cache.clear();fullCache.clear()}
//Concurrency-limited loader
export async function loadWithConcurrency<T>(fn:()=>Promise<T>):Promise<T>{
if(activeLoads>=MAX_CONCURRENT){await new Promise<void>(r=>queue.push(r))}
activeLoads++
try{return await fn()}
finally{activeLoads--;runNext()}
}
