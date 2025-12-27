//Drag context for cross-component drag state (uses mouse events to bypass PyWebView/WebKit drag limitations)
import{createContext,useContext,useState,useCallback,useEffect,useRef,type ReactNode}from'react'
export type DragDataType='asset'|'template'|'product'
export interface DragData{type:DragDataType;path:string}
type DropHandler=(data:DragData)=>void
interface DragContextValue{dragData:DragData|null;setDragData:(d:DragData|null)=>void;clearDrag:()=>void;getDragData:()=>DragData|null;registerDropZone:(id:string,el:HTMLElement,handler:DropHandler)=>void;unregisterDropZone:(id:string)=>void}
const DragContext=createContext<DragContextValue|null>(null)
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
useEffect(()=>{const onMouseUp=(e:MouseEvent)=>{const data=dragDataRef.current;if(!data)return;let handled=false;dropZonesRef.current.forEach(({el,handler})=>{const rect=el.getBoundingClientRect();if(e.clientX>=rect.left&&e.clientX<=rect.right&&e.clientY>=rect.top&&e.clientY<=rect.bottom){handler(data);handled=true}});if(!handled)dragDataRef.current=null;setDragDataState(null);document.body.classList.remove('is-dragging')};document.addEventListener('mouseup',onMouseUp);return()=>document.removeEventListener('mouseup',onMouseUp)},[])
return<DragContext.Provider value={{dragData,setDragData,clearDrag,getDragData,registerDropZone,unregisterDropZone}}>{children}</DragContext.Provider>
}
export function useDrag(){const ctx=useContext(DragContext);if(!ctx)throw new Error('useDrag must be used within DragProvider');return ctx}
