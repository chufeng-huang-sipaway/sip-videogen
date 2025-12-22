//Hook for managing async action states (loading, error, reset)
import{useState,useCallback,useRef,useEffect}from'react'
export interface UseAsyncActionOptions<T>{onSuccess?:(result:T)=>void;onError?:(error:Error)=>void;successMessage?:string}
export interface UseAsyncActionReturn<T,Args extends unknown[]>{execute:(...args:Args)=>Promise<T|undefined>;isLoading:boolean;error:string|null;clearError:()=>void;reset:()=>void}
export function useAsyncAction<T,Args extends unknown[]=[]>(action:(...args:Args)=>Promise<T>,options:UseAsyncActionOptions<T>={}):UseAsyncActionReturn<T,Args>{
const[isLoading,setIsLoading]=useState(false)
const[error,setError]=useState<string|null>(null)
const unmountedRef=useRef(false)
useEffect(()=>{unmountedRef.current=false;return()=>{unmountedRef.current=true}},[])
const execute=useCallback(async(...args:Args):Promise<T|undefined>=>{
if(unmountedRef.current)return undefined
setError(null)
setIsLoading(true)
try{const result=await action(...args)
if(!unmountedRef.current){options.onSuccess?.(result)}
return result
}catch(err){const message=err instanceof Error?err.message:'An error occurred'
if(!unmountedRef.current){setError(message);options.onError?.(err instanceof Error?err:new Error(message))}
return undefined
}finally{if(!unmountedRef.current)setIsLoading(false)}
},[action,options])
const clearError=useCallback(()=>setError(null),[])
const reset=useCallback(()=>{setError(null);setIsLoading(false)},[])
return{execute,isLoading,error,clearError,reset}}
