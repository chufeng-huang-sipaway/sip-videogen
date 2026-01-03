/* eslint-disable react-refresh/only-export-components */
import{createContext,useContext,useState,useCallback}from'react'
import type{ReactNode}from'react'
//Viewer state for zoom, pan, fullscreen, info overlay
export interface ViewerState{zoom:number;panX:number;panY:number;isFullscreen:boolean;showInfo:boolean;naturalW:number|null;naturalH:number|null;containerW:number;containerH:number;isPanning:boolean}
interface ViewerContextType extends ViewerState{setZoom:(z:number)=>void;setPan:(x:number,y:number)=>void;zoomIn:()=>void;zoomOut:()=>void;zoomToFit:()=>void;zoomToActual:()=>void;toggleFullscreen:()=>void;toggleInfo:()=>void;resetView:()=>void;clearDimensions:()=>void;setNaturalSize:(w:number,h:number)=>void;setContainerSize:(w:number,h:number)=>void;setIsPanning:(v:boolean)=>void;getFitScale:()=>number;getDisplayPercent:()=>number;clampPan:()=>void}
const ViewerContext=createContext<ViewerContextType|null>(null)
const ZOOM_MIN=1,ZOOM_MAX=5,ZOOM_STEP=1.25
export function ViewerProvider({children}:{children:ReactNode}){
const[state,setState]=useState<ViewerState>({zoom:1,panX:0,panY:0,isFullscreen:false,showInfo:false,naturalW:null,naturalH:null,containerW:0,containerH:0,isPanning:false})
//Get fit scale: min(container/natural, 1) - never upscale beyond 100%
const getFitScale=useCallback(():number=>{const{naturalW,naturalH,containerW,containerH}=state;if(!naturalW||!naturalH||containerW<=0||containerH<=0)return 1;return Math.min(containerW/naturalW,containerH/naturalH,1)},[state])
//Display percentage = fitScale * zoom * 100
const getDisplayPercent=useCallback(():number=>Math.round(getFitScale()*state.zoom*100),[getFitScale,state.zoom])
const setZoom=useCallback((z:number)=>{setState(s=>({...s,zoom:Math.max(ZOOM_MIN,Math.min(ZOOM_MAX,z))}))},[])
const setPan=useCallback((x:number,y:number)=>{setState(s=>({...s,panX:x,panY:y}))},[])
const zoomIn=useCallback(()=>{setState(s=>({...s,zoom:Math.min(ZOOM_MAX,s.zoom*ZOOM_STEP)}))},[])
const zoomOut=useCallback(()=>{setState(s=>({...s,zoom:Math.max(ZOOM_MIN,s.zoom/ZOOM_STEP)}))},[])
const zoomToFit=useCallback(()=>{setState(s=>({...s,zoom:1,panX:0,panY:0}))},[])
//Zoom to actual size: zoom = 1/fitScale (clamped)
const zoomToActual=useCallback(()=>{setState(s=>{const{naturalW,naturalH,containerW,containerH}=s;if(!naturalW||!naturalH||containerW<=0||containerH<=0)return s;const fitScale=Math.min(containerW/naturalW,containerH/naturalH,1);const targetZoom=Math.min(ZOOM_MAX,1/fitScale);return{...s,zoom:targetZoom,panX:0,panY:0}})},[])
const toggleFullscreen=useCallback(()=>{setState(s=>({...s,isFullscreen:!s.isFullscreen}))},[])
const toggleInfo=useCallback(()=>{setState(s=>({...s,showInfo:!s.showInfo}))},[])
const resetView=useCallback(()=>{setState(s=>({...s,zoom:1,panX:0,panY:0}))},[])
const clearDimensions=useCallback(()=>{setState(s=>({...s,naturalW:null,naturalH:null}))},[])
const setNaturalSize=useCallback((w:number,h:number)=>{setState(s=>({...s,naturalW:w,naturalH:h}))},[])
const setContainerSize=useCallback((w:number,h:number)=>{setState(s=>({...s,containerW:w,containerH:h}))},[])
const setIsPanning=useCallback((v:boolean)=>{setState(s=>({...s,isPanning:v}))},[])
//Clamp pan to keep image visible
const clampPan=useCallback(()=>{setState(s=>{if(!s.naturalW||!s.naturalH)return s;const maxPanX=(s.naturalW*s.zoom)/2,maxPanY=(s.naturalH*s.zoom)/2;return{...s,panX:Math.max(-maxPanX,Math.min(maxPanX,s.panX)),panY:Math.max(-maxPanY,Math.min(maxPanY,s.panY))}})},[])
return(<ViewerContext.Provider value={{...state,setZoom,setPan,zoomIn,zoomOut,zoomToFit,zoomToActual,toggleFullscreen,toggleInfo,resetView,clearDimensions,setNaturalSize,setContainerSize,setIsPanning,getFitScale,getDisplayPercent,clampPan}}>{children}</ViewerContext.Provider>)}
export function useViewer(){const ctx=useContext(ViewerContext);if(!ctx)throw new Error('useViewer must be used within a ViewerProvider');return ctx}
