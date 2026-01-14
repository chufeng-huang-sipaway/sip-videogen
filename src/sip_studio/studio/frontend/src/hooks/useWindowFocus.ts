import{useEffect}from 'react'
//Track window focus/blur and set data attribute on document root
export function useWindowFocus(){
useEffect(()=>{
const set=(f:boolean)=>{document.documentElement.dataset.windowFocused=String(f)}
set(document.hasFocus())
const onFocus=()=>set(true)
const onBlur=()=>set(false)
window.addEventListener('focus',onFocus)
window.addEventListener('blur',onBlur)
return()=>{window.removeEventListener('focus',onFocus);window.removeEventListener('blur',onBlur)}
},[])
}
