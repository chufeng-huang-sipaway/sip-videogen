//Drag context for cross-component drag state (uses mouse events to bypass PyWebView/WebKit drag limitations)
import{createContext,useContext,useState,useCallback,useEffect,useRef,type ReactNode}from'react'
export type DragDataType='asset'|'style-reference'|'product'
export interface DragData{type:DragDataType;path:string;thumbnailUrl?:string}
type DropHandler=(data:DragData)=>void
interface DragContextValue{dragData:DragData|null;setDragData:(d:DragData|null)=>void;clearDrag:()=>void;getDragData:()=>DragData|null;registerDropZone:(id:string,el:HTMLElement,handler:DropHandler)=>void;unregisterDropZone:(id:string)=>void}
const DragContext=createContext<DragContextValue|null>(null)
//Floating drag preview component
function DragPreview({thumbnailUrl}:{thumbnailUrl:string}){
const[pos,setPos]=useState({x:0,y:0})
useEffect(()=>{const onMove=(e:MouseEvent)=>setPos({x:e.clientX,y:e.clientY});document.addEventListener('mousemove',onMove);return()=>document.removeEventListener('mousemove',onMove)},[])
if(!pos.x&&!pos.y)return null
return<div style={{position:'fixed',left:pos.x+12,top:pos.y+12,pointerEvents:'none',zIndex:9999}} className="w-20 h-20 rounded-lg shadow-2xl overflow-hidden ring-2 ring-white/50 opacity-90"><img src={thumbnailUrl} alt="" className="w-full h-full object-cover"/></div>
}
export function DragProvider({children}:{children:ReactNode}){
const[dragData,setDragDataState]=useState<DragData|null>(null)
const dragDataRef=useRef<DragData|null>(null)
const dropZonesRef=useRef<Map<string,{el:HTMLElement;handler:DropHandler}>>(new Map())
const setDragData=useCallback((d:DragData|null)=>{dragDataRef.current=d;setDragDataState(d);if(d)document.body.classList.add('is-dragging');else document.body.classList.remove('is-dragging')},[])
const clearDrag=useCallback(()=>{dragDataRef.current=null;setDragDataState(null);document.body.classList.remove('is-dragging')},[])
const getDragData=useCallback(()=>dragDataRef.current,[])
const registerDropZone=useCallback((id:string,el:HTMLElement,handler:DropHandler)=>{dropZonesRef.current.set(id,{el,handler})},[])
const unregisterDropZone=useCallback((id:string)=>{dropZonesRef.current.delete(id)},[])
//Global mouseup listener - check if release is over a drop zone
useEffect(()=>{const onMouseUp=(e:MouseEvent)=>{const data=dragDataRef.current;if(!data)return;dropZonesRef.current.forEach(({el,handler})=>{const rect=el.getBoundingClientRect();if(e.clientX>=rect.left&&e.clientX<=rect.right&&e.clientY>=rect.top&&e.clientY<=rect.bottom){handler(data)}});dragDataRef.current=null;setDragDataState(null);document.body.classList.remove('is-dragging')};document.addEventListener('mouseup',onMouseUp);return()=>document.removeEventListener('mouseup',onMouseUp)},[])
return<DragContext.Provider value={{dragData,setDragData,clearDrag,getDragData,registerDropZone,unregisterDropZone}}>{children}{dragData?.thumbnailUrl&&<DragPreview thumbnailUrl={dragData.thumbnailUrl}/>}</DragContext.Provider>
}
export function useDrag(){const ctx=useContext(DragContext);if(!ctx)throw new Error('useDrag must be used within DragProvider');return ctx}
