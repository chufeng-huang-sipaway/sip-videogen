/* eslint-disable react-refresh/only-export-components */
import{createContext,useContext,useState,useCallback}from'react'
import type{ReactNode}from'react'
//Image data interface
export interface GeneratedImage{id:string;path:string;prompt?:string;sourceTemplatePath?:string;timestamp:string;trashedAt?:string}
//Workstation state interface
export interface WorkstationState{currentBatch:GeneratedImage[];selectedIndex:number;viewMode:'single'|'comparison';comparisonSource:string|null;unsortedImages:GeneratedImage[];isTrashView:boolean;statusVersion:number}
interface WorkstationContextType extends WorkstationState{setCurrentBatch:(images:GeneratedImage[])=>void;setSelectedIndex:(index:number)=>void;setViewMode:(mode:'single'|'comparison')=>void;setComparisonSource:(path:string|null)=>void;addToUnsorted:(images:GeneratedImage[])=>void;removeFromUnsorted:(imageId:string)=>void;clearCurrentBatch:()=>void;setIsTrashView:(isTrash:boolean)=>void;bumpStatusVersion:()=>void}
const WorkstationContext=createContext<WorkstationContextType|null>(null)
export function WorkstationProvider({children}:{children:ReactNode}){
const[currentBatch,setCurrentBatchState]=useState<GeneratedImage[]>([])
const[selectedIndex,setSelectedIndexState]=useState(0)
const[viewMode,setViewModeState]=useState<'single'|'comparison'>('single')
const[comparisonSource,setComparisonSourceState]=useState<string|null>(null)
const[unsortedImages,setUnsortedImages]=useState<GeneratedImage[]>([])
const[isTrashView,setIsTrashViewState]=useState(false)
const[statusVersion,setStatusVersion]=useState(0)
const setCurrentBatch=useCallback((images:GeneratedImage[])=>{setCurrentBatchState(images);setSelectedIndexState(0)},[])
const setIsTrashView=useCallback((isTrash:boolean)=>{setIsTrashViewState(isTrash)},[])
const setSelectedIndex=useCallback((index:number)=>{setSelectedIndexState(Math.max(0,Math.min(index,currentBatch.length-1)))},[currentBatch.length])
const setViewMode=useCallback((mode:'single'|'comparison')=>{setViewModeState(mode)},[])
const setComparisonSource=useCallback((path:string|null)=>{setComparisonSourceState(path)},[])
const addToUnsorted=useCallback((images:GeneratedImage[])=>{setUnsortedImages(prev=>[...prev,...images])},[])
const removeFromUnsorted=useCallback((imageId:string)=>{setUnsortedImages(prev=>prev.filter(img=>img.id!==imageId))},[])
const clearCurrentBatch=useCallback(()=>{setCurrentBatchState([]);setSelectedIndexState(0);setIsTrashViewState(false)},[])
const bumpStatusVersion=useCallback(()=>{setStatusVersion(prev=>prev+1)},[])
return(<WorkstationContext.Provider value={{currentBatch,selectedIndex,viewMode,comparisonSource,unsortedImages,isTrashView,statusVersion,setCurrentBatch,setSelectedIndex,setViewMode,setComparisonSource,addToUnsorted,removeFromUnsorted,clearCurrentBatch,setIsTrashView,bumpStatusVersion}}>{children}</WorkstationContext.Provider>)}
export function useWorkstation(){const context=useContext(WorkstationContext);if(!context)throw new Error('useWorkstation must be used within a WorkstationProvider');return context}
