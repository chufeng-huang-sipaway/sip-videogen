import{useEffect,useRef}from'react'
import{bridge,isPyWebView,type WindowBounds}from'../lib/bridge'
//Debounce delay for resize events (ms)
const DEBOUNCE_MS=500
/**
 * Hook to persist window bounds on resize.
 * Reports window position and size to Python backend via bridge.
 * Uses debouncing to avoid excessive writes.
 */
export function useWindowResize(){
  const timeoutRef=useRef<number|null>(null)
  useEffect(()=>{
    if(!isPyWebView())return
    const reportBounds=()=>{
      const bounds:WindowBounds={
        x:window.screenX,
        y:window.screenY,
        width:window.innerWidth,
        height:window.innerHeight,
      }
      bridge.saveWindowBounds(bounds).catch(e=>{
        console.debug('[useWindowResize] Failed to save bounds:',e)
      })
    }
    const debouncedReport=()=>{
      if(timeoutRef.current)window.clearTimeout(timeoutRef.current)
      timeoutRef.current=window.setTimeout(reportBounds,DEBOUNCE_MS)
    }
    window.addEventListener('resize',debouncedReport)
    //Also save on beforeunload to capture final position
    window.addEventListener('beforeunload',reportBounds)
    return()=>{
      window.removeEventListener('resize',debouncedReport)
      window.removeEventListener('beforeunload',reportBounds)
      if(timeoutRef.current)window.clearTimeout(timeoutRef.current)
    }
  },[])
}
