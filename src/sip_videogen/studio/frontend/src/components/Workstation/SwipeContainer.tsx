//SwipeContainer - wrap images for swipe gesture keep/trash curation
import{useRef,useState,useCallback,type ReactNode,type MouseEvent,type TouchEvent}from'react'
interface SwipeContainerProps{children:ReactNode;onSwipeRight:()=>void;onSwipeLeft:()=>void;threshold?:number;disabled?:boolean}
interface SwipeState{isDragging:boolean;startX:number;currentX:number;startY:number}
export function SwipeContainer({children,onSwipeRight,onSwipeLeft,threshold=100,disabled=false}:SwipeContainerProps){
const ref=useRef<HTMLDivElement>(null)
const[state,setState]=useState<SwipeState>({isDragging:false,startX:0,currentX:0,startY:0})
const offset=state.isDragging?state.currentX-state.startX:0
const absOffset=Math.abs(offset)
const progress=Math.min(absOffset/threshold,1)
const rotation=offset/20
//Mouse handlers
const handleMouseDown=useCallback((e:MouseEvent)=>{if(disabled)return;setState({isDragging:true,startX:e.clientX,currentX:e.clientX,startY:e.clientY})},[disabled])
const handleMouseMove=useCallback((e:MouseEvent)=>{if(!state.isDragging||disabled)return;setState(s=>({...s,currentX:e.clientX}))},[state.isDragging,disabled])
const handleMouseUp=useCallback(()=>{if(!state.isDragging||disabled)return;if(offset>=threshold)onSwipeRight();else if(offset<=-threshold)onSwipeLeft();setState({isDragging:false,startX:0,currentX:0,startY:0})},[state.isDragging,offset,threshold,onSwipeRight,onSwipeLeft,disabled])
const handleMouseLeave=useCallback(()=>{if(state.isDragging)setState({isDragging:false,startX:0,currentX:0,startY:0})},[state.isDragging])
//Touch handlers
const handleTouchStart=useCallback((e:TouchEvent)=>{if(disabled||!e.touches[0])return;setState({isDragging:true,startX:e.touches[0].clientX,currentX:e.touches[0].clientX,startY:e.touches[0].clientY})},[disabled])
const handleTouchMove=useCallback((e:TouchEvent)=>{if(!state.isDragging||disabled||!e.touches[0])return;setState(s=>({...s,currentX:e.touches[0].clientX}))},[state.isDragging,disabled])
const handleTouchEnd=useCallback(()=>{if(!state.isDragging||disabled)return;if(offset>=threshold)onSwipeRight();else if(offset<=-threshold)onSwipeLeft();setState({isDragging:false,startX:0,currentX:0,startY:0})},[state.isDragging,offset,threshold,onSwipeRight,onSwipeLeft,disabled])
//Visual feedback colors
const bgColor=offset>0?`rgba(34,197,94,${progress*0.3})`:offset<0?`rgba(239,68,68,${progress*0.3})`:'transparent'
const borderColor=offset>0?`rgba(34,197,94,${progress})`:`rgba(239,68,68,${progress})`
return(<div ref={ref} className="relative flex-1 flex items-center justify-center select-none cursor-grab active:cursor-grabbing" style={{background:bgColor}} onMouseDown={handleMouseDown} onMouseMove={handleMouseMove} onMouseUp={handleMouseUp} onMouseLeave={handleMouseLeave} onTouchStart={handleTouchStart} onTouchMove={handleTouchMove} onTouchEnd={handleTouchEnd}><div className="relative transition-transform" style={{transform:`translateX(${offset}px) rotate(${rotation}deg)`,transition:state.isDragging?'none':'transform 0.3s ease-out',border:absOffset>10?`2px solid ${borderColor}`:'2px solid transparent',borderRadius:'0.5rem',padding:'0.25rem'}}>{children}{absOffset>30&&(<div className="absolute inset-0 flex items-center justify-center pointer-events-none"><div className={`text-2xl font-bold uppercase tracking-wider px-4 py-2 rounded border-4 ${offset>0?'text-green-500 border-green-500 bg-green-500/20 rotate-[-15deg]':'text-red-500 border-red-500 bg-red-500/20 rotate-[15deg]'}`} style={{opacity:progress}}>{offset>0?'Keep':'Trash'}</div></div>)}</div></div>)}
