//SwipeContainer - wrap images for swipe gesture keep/trash curation with slide-out animation and trackpad support
import{useRef,useState,useCallback,useEffect,type ReactNode,type MouseEvent,type TouchEvent}from'react'
import{ChevronLeft,ChevronRight}from'lucide-react'
interface SwipeContainerProps{children:ReactNode;onSwipeRight:()=>void;onSwipeLeft:()=>void;threshold?:number;disabled?:boolean;mode?:'curate'|'navigate'}
interface SwipeState{isDragging:boolean;startX:number;currentX:number;startY:number;exitDir:'left'|'right'|null;isHovered:boolean;wheelDelta:number;isWheelSwiping:boolean}
export function SwipeContainer({children,onSwipeRight,onSwipeLeft,threshold=100,disabled=false,mode='curate'}:SwipeContainerProps){
const isNavigateMode=mode==='navigate'
const ref=useRef<HTMLDivElement>(null)
const wheelTimeoutRef=useRef<number|null>(null)
const wheelDeltaRef=useRef(0)
const isHoveredRef=useRef(false)
const isDraggingRef=useRef(false)
const exitDirRef=useRef<'left'|'right'|null>(null)
const[state,setState]=useState<SwipeState>({isDragging:false,startX:0,currentX:0,startY:0,exitDir:null,isHovered:false,wheelDelta:0,isWheelSwiping:false})
//Sync refs with state
useEffect(()=>{isHoveredRef.current=state.isHovered},[state.isHovered])
useEffect(()=>{isDraggingRef.current=state.isDragging},[state.isDragging])
useEffect(()=>{exitDirRef.current=state.exitDir},[state.exitDir])
//Calculate effective offset (from drag or wheel)
const dragOffset=state.isDragging?state.currentX-state.startX:0
const effectiveOffset=state.exitDir?(state.exitDir==='right'?500:-500):state.isDragging?dragOffset:state.isWheelSwiping?state.wheelDelta:0
const absOffset=Math.abs(state.isDragging?dragOffset:state.isWheelSwiping?state.wheelDelta:0)
const progress=Math.min(absOffset/threshold,1)
const rotation=state.exitDir?(state.exitDir==='right'?25:-25):effectiveOffset/20
//Mouse drag handlers
const handleMouseDown=useCallback((e:MouseEvent)=>{if(disabled||state.exitDir||state.isWheelSwiping)return;setState(s=>({...s,isDragging:true,startX:e.clientX,currentX:e.clientX,startY:e.clientY}))},[disabled,state.exitDir,state.isWheelSwiping])
const handleMouseMove=useCallback((e:MouseEvent)=>{if(!state.isDragging||disabled||state.exitDir)return;setState(s=>({...s,currentX:e.clientX}))},[state.isDragging,disabled,state.exitDir])
const handleMouseUp=useCallback(()=>{if(!state.isDragging||disabled||state.exitDir)return;const o=state.currentX-state.startX;if(o>=threshold){setState(s=>({...s,isDragging:false,exitDir:'right'}))}else if(o<=-threshold){setState(s=>({...s,isDragging:false,exitDir:'left'}))}else{setState(s=>({...s,isDragging:false,startX:0,currentX:0,startY:0}))}},[state.isDragging,state.currentX,state.startX,threshold,disabled,state.exitDir])
//Hover handlers
const handleMouseEnter=useCallback(()=>{if(disabled||state.exitDir)return;setState(s=>({...s,isHovered:true}))},[disabled,state.exitDir])
const handleMouseLeave=useCallback(()=>{if(state.exitDir)return;if(wheelTimeoutRef.current){clearTimeout(wheelTimeoutRef.current);wheelTimeoutRef.current=null}
wheelDeltaRef.current=0;setState(s=>s.isDragging?{...s,isDragging:false,startX:0,currentX:0,startY:0}:{...s,isHovered:false,wheelDelta:0,isWheelSwiping:false})},[state.exitDir])
//Touch handlers
const handleTouchStart=useCallback((e:TouchEvent)=>{if(disabled||!e.touches[0]||state.exitDir)return;setState(s=>({...s,isDragging:true,startX:e.touches[0].clientX,currentX:e.touches[0].clientX,startY:e.touches[0].clientY}))},[disabled,state.exitDir])
const handleTouchMove=useCallback((e:TouchEvent)=>{if(!state.isDragging||disabled||!e.touches[0]||state.exitDir)return;setState(s=>({...s,currentX:e.touches[0].clientX}))},[state.isDragging,disabled,state.exitDir])
const handleTouchEnd=useCallback(()=>{if(!state.isDragging||disabled||state.exitDir)return;const o=state.currentX-state.startX;if(o>=threshold){setState(s=>({...s,isDragging:false,exitDir:'right'}))}else if(o<=-threshold){setState(s=>({...s,isDragging:false,exitDir:'left'}))}else{setState(s=>({...s,isDragging:false,startX:0,currentX:0,startY:0}))}},[state.isDragging,state.currentX,state.startX,threshold,disabled,state.exitDir])
//Handle exit animation completion - centralized callback trigger
useEffect(()=>{if(!state.exitDir)return
const timer=setTimeout(()=>{const dir=state.exitDir;if(dir==='right')onSwipeRight();else if(dir==='left')onSwipeLeft()
wheelDeltaRef.current=0;setState({isDragging:false,startX:0,currentX:0,startY:0,exitDir:null,isHovered:false,wheelDelta:0,isWheelSwiping:false})},300)
return()=>clearTimeout(timer)},[state.exitDir,onSwipeRight,onSwipeLeft])
//Wheel handler for trackpad swipe - stable callback using refs
useEffect(()=>{const el=ref.current;if(!el)return
const handleWheel=(e:WheelEvent)=>{
//Only process when hovering, not dragging, not exiting
if(!isHoveredRef.current||isDraggingRef.current||exitDirRef.current||disabled)return
//Check if horizontal scroll (trackpad two-finger swipe)
const isHorizontal=Math.abs(e.deltaX)>Math.abs(e.deltaY)
if(!isHorizontal||Math.abs(e.deltaX)<2)return
//Prevent default to stop window elastic scrolling
e.preventDefault();e.stopPropagation()
//Accumulate delta (invert: scroll direction opposite to swipe intent)
wheelDeltaRef.current-=e.deltaX
//Update visual state
setState(s=>({...s,wheelDelta:wheelDeltaRef.current,isWheelSwiping:true}))
//Debounce: check threshold after gesture pauses
if(wheelTimeoutRef.current)clearTimeout(wheelTimeoutRef.current)
wheelTimeoutRef.current=window.setTimeout(()=>{const delta=wheelDeltaRef.current
if(Math.abs(delta)>=threshold){const dir=delta>=threshold?'right':'left'
wheelDeltaRef.current=0;setState(s=>({...s,exitDir:dir,wheelDelta:0,isWheelSwiping:false}))}else{
wheelDeltaRef.current=0;setState(s=>({...s,wheelDelta:0,isWheelSwiping:false}))}},150)}
el.addEventListener('wheel',handleWheel,{passive:false})
return()=>{el.removeEventListener('wheel',handleWheel);if(wheelTimeoutRef.current){clearTimeout(wheelTimeoutRef.current);wheelTimeoutRef.current=null}}},[disabled,threshold])
//Visual feedback colors - different for navigate vs curate mode
const swipeOffset=state.isDragging?dragOffset:state.isWheelSwiping?state.wheelDelta:0
const bgColor=isNavigateMode?`rgba(59,130,246,${progress*0.15})`:(swipeOffset>0?`rgba(34,197,94,${progress*0.3})`:swipeOffset<0?`rgba(239,68,68,${progress*0.3})`:'transparent')
const borderColor=isNavigateMode?`rgba(59,130,246,${progress})`:(swipeOffset>0?`rgba(34,197,94,${progress})`:`rgba(239,68,68,${progress})`)
const exitOpacity=state.exitDir?(isNavigateMode?1:0):1
//In navigate mode, slide but don't fade out; just transition to next image
const navTransform=isNavigateMode?`translateX(${effectiveOffset*0.3}px)`:`translateX(${effectiveOffset}px) rotate(${rotation}deg)`
//Hover glow when ready for swipe
const hoverGlow=state.isHovered&&!state.isDragging&&!state.isWheelSwiping&&!state.exitDir?'0 0 0 2px rgba(147,51,234,0.3)':'none'
return(<div ref={ref} className="absolute inset-4 select-none cursor-grab active:cursor-grabbing overflow-hidden" style={{background:bgColor,transition:'background 0.15s ease-out',display:'flex',alignItems:'center',justifyContent:'center'}} onMouseDown={handleMouseDown} onMouseMove={handleMouseMove} onMouseUp={handleMouseUp} onMouseEnter={handleMouseEnter} onMouseLeave={handleMouseLeave} onTouchStart={handleTouchStart} onTouchMove={handleTouchMove} onTouchEnd={handleTouchEnd}><div className="relative will-change-transform h-full w-full" style={{transform:navTransform,opacity:exitOpacity,transition:state.isDragging||state.isWheelSwiping?'none':'all 0.3s cubic-bezier(0.4,0,0.2,1)',border:absOffset>10?`2px solid ${borderColor}`:'2px solid transparent',boxShadow:hoverGlow,borderRadius:'0.5rem',padding:'0.25rem',display:'flex',alignItems:'center',justifyContent:'center'}}>{children}{absOffset>30&&!state.exitDir&&!isNavigateMode&&(<div className="absolute inset-0 flex items-center justify-center pointer-events-none"><div className={`text-2xl font-bold uppercase tracking-wider px-4 py-2 rounded border-4 transition-opacity duration-150 ${swipeOffset>0?'text-green-500 border-green-500 bg-green-500/20 rotate-[-15deg]':'text-red-500 border-red-500 bg-red-500/20 rotate-[15deg]'}`} style={{opacity:progress}}>{swipeOffset>0?'Keep':'Trash'}</div></div>)}{absOffset>30&&!state.exitDir&&isNavigateMode&&(<div className="absolute inset-0 flex items-center justify-center pointer-events-none"><div className="flex items-center gap-2 text-blue-500 transition-opacity duration-150" style={{opacity:progress}}>{swipeOffset>0?<><ChevronLeft className="w-8 h-8"/><span className="text-lg font-medium">Previous</span></>:<><span className="text-lg font-medium">Next</span><ChevronRight className="w-8 h-8"/></>}</div></div>)}</div></div>)}
