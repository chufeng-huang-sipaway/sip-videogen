/* eslint-disable react-refresh/only-export-components */
import{createContext,useContext,useState,useCallback}from'react'
import type{ReactNode}from'react'
//Image data interface
export interface GeneratedImage{id:string;path:string;originalPath?:string;prompt?:string;sourceTemplatePath?:string;timestamp:string;viewedAt?:string|null}
//Browse mode type for grid/preview toggle
export type BrowseMode='preview'|'grid'
//Workstation state interface
export interface WorkstationState{currentBatch:GeneratedImage[];selectedIndex:number;statusVersion:number;browseMode:BrowseMode}
interface WorkstationContextType extends WorkstationState{setCurrentBatch:(images:GeneratedImage[])=>void;prependToBatch:(images:GeneratedImage[])=>void;setSelectedIndex:(index:number)=>void;clearCurrentBatch:()=>void;bumpStatusVersion:()=>void;updateImagePath:(imageId:string,dataUrl:string)=>void;setBrowseMode:(mode:BrowseMode)=>void;removeFromBatchByPath:(path:string)=>void;markAsViewed:(imageId:string,viewedAt:string)=>void}
const WorkstationContext=createContext<WorkstationContextType|null>(null)
export function WorkstationProvider({children}:{children:ReactNode}){
const[state,setState]=useState<WorkstationState>({currentBatch:[],selectedIndex:0,statusVersion:0,browseMode:'preview'})
const setCurrentBatch=useCallback((images:GeneratedImage[])=>{setState(s=>({...s,currentBatch:images,selectedIndex:0}))},[])
//Prepend new images to existing batch, focus on first new image
const prependToBatch=useCallback((images:GeneratedImage[])=>{setState(s=>({...s,currentBatch:[...images,...s.currentBatch],selectedIndex:0}))},[])
const setSelectedIndex=useCallback((index:number)=>{setState(s=>({...s,selectedIndex:Math.max(0,Math.min(index,s.currentBatch.length-1))}))},[])
const clearCurrentBatch=useCallback(()=>{setState(s=>({...s,currentBatch:[],selectedIndex:0}))},[])
const bumpStatusVersion=useCallback(()=>{setState(s=>({...s,statusVersion:s.statusVersion+1}))},[])
const updateImagePath=useCallback((imageId:string,dataUrl:string)=>{setState(s=>({...s,currentBatch:s.currentBatch.map(img=>img.id===imageId?{...img,path:dataUrl}:img)}))},[])
const setBrowseMode=useCallback((mode:BrowseMode)=>{setState(s=>({...s,browseMode:mode}))},[])
//Atomic remove: updates batch+index together (iOS Photos behavior), robust to async/races by matching on path
const removeFromBatchByPath=useCallback((path:string)=>{setState(s=>{const indexToRemove=s.currentBatch.findIndex(img=>img.originalPath===path||img.path===path);if(indexToRemove<0)return s;const newBatch=s.currentBatch.filter((_,i)=>i!==indexToRemove);const newLen=newBatch.length;let newIndex=s.selectedIndex;if(newLen===0)newIndex=0;else if(s.selectedIndex>indexToRemove)newIndex=s.selectedIndex-1;else if(s.selectedIndex<indexToRemove)newIndex=Math.min(s.selectedIndex,newLen-1);else newIndex=indexToRemove>=newLen?newLen-1:indexToRemove;return{...s,currentBatch:newBatch,selectedIndex:newIndex}})},[])
//Mark image as viewed (read) - update local state optimistically
const markAsViewed=useCallback((imageId:string,viewedAt:string)=>{setState(s=>({...s,currentBatch:s.currentBatch.map(img=>img.id===imageId?{...img,viewedAt}:img)}))},[])
return(<WorkstationContext.Provider value={{...state,setCurrentBatch,prependToBatch,setSelectedIndex,clearCurrentBatch,bumpStatusVersion,updateImagePath,setBrowseMode,removeFromBatchByPath,markAsViewed}}>{children}</WorkstationContext.Provider>)}
export function useWorkstation(){const context=useContext(WorkstationContext);if(!context)throw new Error('useWorkstation must be used within a WorkstationProvider');return context}
