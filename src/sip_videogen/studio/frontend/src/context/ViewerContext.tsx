/* eslint-disable react-refresh/only-export-components */
import{createContext,useContext,useState,useCallback}from'react'
import type{ReactNode}from'react'
//Viewer state for zoom, pan, fullscreen, info overlay
export interface ViewerState{zoom:number;panX:number;panY:number;isFullscreen:boolean;showInfo:boolean;naturalW:number|null;naturalH:number|null;containerW:number;containerH:number;isPanning:boolean}
interface ViewerContextType extends ViewerState{setZoom:(z:number)=>void;setPan:(x:number,y:number)=>void;setZoomAndPan:(z:number,x:number,y:number)=>void;zoomIn:()=>void;zoomOut:()=>void;zoomToFit:()=>void;zoomToActual:()=>void;toggleFullscreen:()=>void;toggleInfo:()=>void;resetView:()=>void;clearDimensions:()=>void;setNaturalSize:(w:number,h:number)=>void;setContainerSize:(w:number,h:number)=>void;setIsPanning:(v:boolean)=>void;getFitScale:()=>number;getDisplayPercent:()=>number;clampPan:()=>void}
const ViewerContext=createContext<ViewerContextType|null>(null)
const ZOOM_MIN=1,ZOOM_MAX=5,ZOOM_STEP=1.25
export function ViewerProvider({children}:{children:ReactNode}){
const[state,setState]=useState<ViewerState>({zoom:1,panX:0,panY:0,isFullscreen:false,showInfo:false,naturalW:null,naturalH:null,containerW:0,containerH:0,isPanning:false})
//Get fit scale: min(container/natural, 1) - never upscale beyond 100%
const getFitScale=useCallback(():number=>{const{naturalW,naturalH,containerW,containerH}=state;if(!naturalW||!naturalH||containerW<=0||containerH<=0)return 1;return Math.min(containerW/naturalW,containerH/naturalH,1)},[state])
//Display percentage = fitScale * zoom * 100
const getDisplayPercent=useCallback(():number=>Math.round(getFitScale()*state.zoom*100),[getFitScale,state.zoom])
const setPan=useCallback((x:number,y:number)=>{setState(s=>({...s,panX:x,panY:y}))},[])
//Helper to clamp pan values for given zoom
const cp=(s:ViewerState,z:number):{panX:number,panY:number}=>{if(!s.naturalW||!s.naturalH||s.containerW<=0||s.containerH<=0)return{panX:s.panX,panY:s.panY};const fitScale=Math.min(s.containerW/s.naturalW,s.containerH/s.naturalH,1),dispW=s.naturalW*fitScale*z,dispH=s.naturalH*fitScale*z,ovX=Math.max(0,dispW-s.containerW),ovY=Math.max(0,dispH-s.containerH),mX=z>1?ovX/(2*z):0,mY=z>1?ovY/(2*z):0;return{panX:Math.max(-mX,Math.min(mX,s.panX)),panY:Math.max(-mY,Math.min(mY,s.panY))}}
const zoomIn=useCallback(()=>{setState(s=>{const nz=Math.min(ZOOM_MAX,s.zoom*ZOOM_STEP),{panX,panY}=cp(s,nz);return{...s,zoom:nz,panX,panY}})},[])
const zoomOut=useCallback(()=>{setState(s=>{const nz=Math.max(ZOOM_MIN,s.zoom/ZOOM_STEP),{panX,panY}=cp(s,nz);return{...s,zoom:nz,panX,panY}})},[])
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
//Clamp pan: limit based on how much scaled image exceeds container (macOS Photos style)
const clampPan=useCallback(()=>{setState(s=>{if(!s.naturalW||!s.naturalH||s.containerW<=0||s.containerH<=0)return s;const fitScale=Math.min(s.containerW/s.naturalW,s.containerH/s.naturalH,1),displayedW=s.naturalW*fitScale*s.zoom,displayedH=s.naturalH*fitScale*s.zoom,overflowX=Math.max(0,displayedW-s.containerW),overflowY=Math.max(0,displayedH-s.containerH),maxPanX=s.zoom>1?overflowX/(2*s.zoom):0,maxPanY=s.zoom>1?overflowY/(2*s.zoom):0;return{...s,panX:Math.max(-maxPanX,Math.min(maxPanX,s.panX)),panY:Math.max(-maxPanY,Math.min(maxPanY,s.panY))}})},[])
//Set zoom and immediately clamp pan (for zoom-out scenarios)
const setZoomAndClamp=useCallback((z:number)=>{setState(s=>{const newZoom=Math.max(ZOOM_MIN,Math.min(ZOOM_MAX,z));if(!s.naturalW||!s.naturalH||s.containerW<=0||s.containerH<=0)return{...s,zoom:newZoom};const fitScale=Math.min(s.containerW/s.naturalW,s.containerH/s.naturalH,1),displayedW=s.naturalW*fitScale*newZoom,displayedH=s.naturalH*fitScale*newZoom,overflowX=Math.max(0,displayedW-s.containerW),overflowY=Math.max(0,displayedH-s.containerH),maxPanX=newZoom>1?overflowX/(2*newZoom):0,maxPanY=newZoom>1?overflowY/(2*newZoom):0;return{...s,zoom:newZoom,panX:Math.max(-maxPanX,Math.min(maxPanX,s.panX)),panY:Math.max(-maxPanY,Math.min(maxPanY,s.panY))}})},[])
//Atomic zoom+pan with clamping - prevents race condition between setZoom and setPan
const setZoomAndPan=useCallback((z:number,x:number,y:number)=>{setState(s=>{const nz=Math.max(ZOOM_MIN,Math.min(ZOOM_MAX,z));if(!s.naturalW||!s.naturalH||s.containerW<=0||s.containerH<=0)return{...s,zoom:nz,panX:x,panY:y};const fitScale=Math.min(s.containerW/s.naturalW,s.containerH/s.naturalH,1),dispW=s.naturalW*fitScale*nz,dispH=s.naturalH*fitScale*nz,ovX=Math.max(0,dispW-s.containerW),ovY=Math.max(0,dispH-s.containerH),mX=nz>1?ovX/(2*nz):0,mY=nz>1?ovY/(2*nz):0;return{...s,zoom:nz,panX:Math.max(-mX,Math.min(mX,x)),panY:Math.max(-mY,Math.min(mY,y))}})},[])
return(<ViewerContext.Provider value={{...state,setZoom:setZoomAndClamp,setPan,setZoomAndPan,zoomIn,zoomOut,zoomToFit,zoomToActual,toggleFullscreen,toggleInfo,resetView,clearDimensions,setNaturalSize,setContainerSize,setIsPanning,getFitScale,getDisplayPercent,clampPan}}>{children}</ViewerContext.Provider>)}
export function useViewer(){const ctx=useContext(ViewerContext);if(!ctx)throw new Error('useViewer must be used within a ViewerProvider');return ctx}
