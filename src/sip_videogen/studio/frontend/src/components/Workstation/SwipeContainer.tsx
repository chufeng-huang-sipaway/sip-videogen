//SwipeContainer - wrap images for swipe gesture keep/trash curation with slide-out animation
import{useRef,useState,useCallback,type ReactNode,type MouseEvent,type TouchEvent}from'react'
interface SwipeContainerProps{children:ReactNode;onSwipeRight:()=>void;onSwipeLeft:()=>void;threshold?:number;disabled?:boolean}
interface SwipeState{isDragging:boolean;startX:number;currentX:number;startY:number;exitDir:'left'|'right'|null}
export function SwipeContainer({children,onSwipeRight,onSwipeLeft,threshold=100,disabled=false}:SwipeContainerProps){
const ref=useRef<HTMLDivElement>(null)
const[state,setState]=useState<SwipeState>({isDragging:false,startX:0,currentX:0,startY:0,exitDir:null})
const offset=state.exitDir?state.exitDir==='right'?500:-500:state.isDragging?state.currentX-state.startX:0
const absOffset=Math.abs(state.isDragging?state.currentX-state.startX:0)
const progress=Math.min(absOffset/threshold,1)
const rotation=state.exitDir?state.exitDir==='right'?25:-25:offset/20
//Mouse handlers
const handleMouseDown=useCallback((e:MouseEvent)=>{if(disabled||state.exitDir)return;setState({isDragging:true,startX:e.clientX,currentX:e.clientX,startY:e.clientY,exitDir:null})},[disabled,state.exitDir])
const handleMouseMove=useCallback((e:MouseEvent)=>{if(!state.isDragging||disabled||state.exitDir)return;setState(s=>({...s,currentX:e.clientX}))},[state.isDragging,disabled,state.exitDir])
const handleMouseUp=useCallback(()=>{if(!state.isDragging||disabled||state.exitDir)return;const o=state.currentX-state.startX;if(o>=threshold){setState(s=>({...s,isDragging:false,exitDir:'right'}));setTimeout(()=>{onSwipeRight();setState({isDragging:false,startX:0,currentX:0,startY:0,exitDir:null})},300)}else if(o<=-threshold){setState(s=>({...s,isDragging:false,exitDir:'left'}));setTimeout(()=>{onSwipeLeft();setState({isDragging:false,startX:0,currentX:0,startY:0,exitDir:null})},300)}else{setState({isDragging:false,startX:0,currentX:0,startY:0,exitDir:null})}},[state.isDragging,state.currentX,state.startX,threshold,onSwipeRight,onSwipeLeft,disabled,state.exitDir])
const handleMouseLeave=useCallback(()=>{if(state.isDragging&&!state.exitDir)setState({isDragging:false,startX:0,currentX:0,startY:0,exitDir:null})},[state.isDragging,state.exitDir])
//Touch handlers
const handleTouchStart=useCallback((e:TouchEvent)=>{if(disabled||!e.touches[0]||state.exitDir)return;setState({isDragging:true,startX:e.touches[0].clientX,currentX:e.touches[0].clientX,startY:e.touches[0].clientY,exitDir:null})},[disabled,state.exitDir])
const handleTouchMove=useCallback((e:TouchEvent)=>{if(!state.isDragging||disabled||!e.touches[0]||state.exitDir)return;setState(s=>({...s,currentX:e.touches[0].clientX}))},[state.isDragging,disabled,state.exitDir])
const handleTouchEnd=useCallback(()=>{if(!state.isDragging||disabled||state.exitDir)return;const o=state.currentX-state.startX;if(o>=threshold){setState(s=>({...s,isDragging:false,exitDir:'right'}));setTimeout(()=>{onSwipeRight();setState({isDragging:false,startX:0,currentX:0,startY:0,exitDir:null})},300)}else if(o<=-threshold){setState(s=>({...s,isDragging:false,exitDir:'left'}));setTimeout(()=>{onSwipeLeft();setState({isDragging:false,startX:0,currentX:0,startY:0,exitDir:null})},300)}else{setState({isDragging:false,startX:0,currentX:0,startY:0,exitDir:null})}},[state.isDragging,state.currentX,state.startX,threshold,onSwipeRight,onSwipeLeft,disabled,state.exitDir])
//Visual feedback colors
const dragOffset=state.isDragging?state.currentX-state.startX:0
const bgColor=dragOffset>0?`rgba(34,197,94,${progress*0.3})`:dragOffset<0?`rgba(239,68,68,${progress*0.3})`:'transparent'
const borderColor=dragOffset>0?`rgba(34,197,94,${progress})`:`rgba(239,68,68,${progress})`
const exitOpacity=state.exitDir?0:1
return(<div ref={ref} className="absolute inset-4 select-none cursor-grab active:cursor-grabbing overflow-hidden" style={{background:bgColor,transition:'background 0.15s ease-out',display:'flex',alignItems:'center',justifyContent:'center'}} onMouseDown={handleMouseDown} onMouseMove={handleMouseMove} onMouseUp={handleMouseUp} onMouseLeave={handleMouseLeave} onTouchStart={handleTouchStart} onTouchMove={handleTouchMove} onTouchEnd={handleTouchEnd}><div className="relative will-change-transform h-full w-full" style={{transform:`translateX(${offset}px) rotate(${rotation}deg)`,opacity:exitOpacity,transition:state.isDragging?'none':'all 0.3s cubic-bezier(0.4,0,0.2,1)',border:absOffset>10?`2px solid ${borderColor}`:'2px solid transparent',borderRadius:'0.5rem',padding:'0.25rem',display:'flex',alignItems:'center',justifyContent:'center'}}>{children}{absOffset>30&&!state.exitDir&&(<div className="absolute inset-0 flex items-center justify-center pointer-events-none"><div className={`text-2xl font-bold uppercase tracking-wider px-4 py-2 rounded border-4 transition-opacity duration-150 ${dragOffset>0?'text-green-500 border-green-500 bg-green-500/20 rotate-[-15deg]':'text-red-500 border-red-500 bg-red-500/20 rotate-[15deg]'}`} style={{opacity:progress}}>{dragOffset>0?'Keep':'Trash'}</div></div>)}</div></div>)}
