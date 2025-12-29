/* eslint-disable react-refresh/only-export-components */
import{createContext,useContext,useState,useEffect,useCallback,useRef}from'react'
import type{ReactNode}from'react'
import{useBrand}from'@/context/BrandContext'
import type{Tab,TabType}from'@/types/tabs'
import{makeTabId}from'@/types/tabs'
import{AlertDialog,AlertDialogContent,AlertDialogHeader,AlertDialogTitle,AlertDialogDescription,AlertDialogFooter,AlertDialogCancel,AlertDialogAction}from'@/components/ui/alert-dialog'
//Pending close action for async confirm dialog
type PendingCloseAction={type:'single';tabId:string}|{type:'all'}|{type:'others';keepTabId:string}|{type:'brand-switch';newBrand:string}|null
interface TabContextType{tabs:Tab[];activeTabId:string|null;openTab:(type:TabType,slug:string,title:string)=>void;closeTab:(tabId:string)=>void;requestCloseTab:(tabId:string)=>void;closeAllTabs:()=>void;requestCloseAllTabs:()=>void;closeOtherTabs:(keepTabId:string)=>void;requestCloseOtherTabs:(keepTabId:string)=>void;setActiveTab:(tabId:string)=>void;setTabDirty:(tabId:string,isDirty:boolean)=>void;updateTabTitle:(tabId:string,newTitle:string)=>void;requestBrandSwitch:(newBrand:string)=>Promise<boolean>}
const TabContext=createContext<TabContextType|null>(null)
const STORAGE_PREFIX='tabs:'
function getStorageKey(brand:string){return`${STORAGE_PREFIX}${brand}`}
function loadTabsFromStorage(brand:string):{tabs:Tab[];activeTabId:string|null}{
try{const raw=localStorage.getItem(getStorageKey(brand));if(!raw)return{tabs:[],activeTabId:null}
const data=JSON.parse(raw);if(!Array.isArray(data.tabs))return{tabs:[],activeTabId:null}
//Validate tab structure, skip invalid entries
const validTabs=data.tabs.filter((t:unknown)=>t&&typeof t==='object'&&'id'in(t as object)&&'type'in(t as object)&&'slug'in(t as object)&&'title'in(t as object)).map((t:Tab)=>({...t,isDirty:false}))//Reset dirty on load
return{tabs:validTabs,activeTabId:typeof data.activeTabId==='string'?data.activeTabId:null}
}catch{return{tabs:[],activeTabId:null}}}
function saveTabsToStorage(brand:string,tabs:Tab[],activeTabId:string|null){
try{localStorage.setItem(getStorageKey(brand),JSON.stringify({tabs:tabs.map(t=>({id:t.id,type:t.type,slug:t.slug,title:t.title,isDirty:false})),activeTabId}))}catch{/*ignore storage errors*/}}
export function TabProvider({children}:{children:ReactNode}){
const{activeBrand,selectBrand}=useBrand()
const[tabs,setTabs]=useState<Tab[]>([])
const[activeTabId,setActiveTabId]=useState<string|null>(null)
const[pendingClose,setPendingClose]=useState<PendingCloseAction>(null)
const prevBrandRef=useRef<string|null>(null)
const brandSwitchResolveRef=useRef<((proceed:boolean)=>void)|null>(null)
//Load tabs when brand changes
useEffect(()=>{if(!activeBrand){setTabs([]);setActiveTabId(null);return}
//Skip if same brand (prevent double-load)
if(prevBrandRef.current===activeBrand)return
prevBrandRef.current=activeBrand
const{tabs:loaded,activeTabId:loadedActive}=loadTabsFromStorage(activeBrand)
setTabs(loaded);setActiveTabId(loadedActive)},[activeBrand])
//Save tabs whenever they change
useEffect(()=>{if(activeBrand)saveTabsToStorage(activeBrand,tabs,activeTabId)},[activeBrand,tabs,activeTabId])
//Count dirty tabs
const dirtyCount=tabs.filter(t=>t.isDirty).length
const getDirtyCountFor=(tabIds:string[])=>tabs.filter(t=>tabIds.includes(t.id)&&t.isDirty).length
//Open tab (or focus existing)
const openTab=useCallback((type:TabType,slug:string,title:string)=>{if(!activeBrand)return
const id=makeTabId(activeBrand,type,slug)
setTabs(prev=>{const exists=prev.find(t=>t.id===id);if(exists)return prev
return[...prev,{id,type,slug,title,isDirty:false}]})
setActiveTabId(id)},[activeBrand])
//Actual close (no confirmation)
const closeTab=useCallback((tabId:string)=>{setTabs(prev=>{const idx=prev.findIndex(t=>t.id===tabId);if(idx===-1)return prev
const next=prev.filter(t=>t.id!==tabId)
//Focus adjacent tab if closing active
setActiveTabId(curr=>{if(curr!==tabId)return curr
if(next.length===0)return null
//Try right, then left
const rightIdx=Math.min(idx,next.length-1)
return next[rightIdx]?.id??null})
return next})},[])
//Request close (checks dirty first)
const requestCloseTab=useCallback((tabId:string)=>{const tab=tabs.find(t=>t.id===tabId);if(!tab)return
if(tab.isDirty){setPendingClose({type:'single',tabId})}else{closeTab(tabId)}},[tabs,closeTab])
//Close all tabs (no confirmation)
const closeAllTabs=useCallback(()=>{setTabs([]);setActiveTabId(null)},[])
//Request close all (checks dirty first)
const requestCloseAllTabs=useCallback(()=>{if(dirtyCount>0){setPendingClose({type:'all'})}else{closeAllTabs()}},[dirtyCount,closeAllTabs])
//Close others (no confirmation)
const closeOtherTabs=useCallback((keepTabId:string)=>{setTabs(prev=>prev.filter(t=>t.id===keepTabId));setActiveTabId(keepTabId)},[])
//Request close others (checks dirty first)
const requestCloseOtherTabs=useCallback((keepTabId:string)=>{const otherIds=tabs.filter(t=>t.id!==keepTabId).map(t=>t.id)
const otherDirtyCount=getDirtyCountFor(otherIds)
if(otherDirtyCount>0){setPendingClose({type:'others',keepTabId})}else{closeOtherTabs(keepTabId)}},[tabs,closeOtherTabs])
//Set tab dirty
const setTabDirty=useCallback((tabId:string,isDirty:boolean)=>{setTabs(prev=>prev.map(t=>t.id===tabId?{...t,isDirty}:t))},[])
//Update tab title
const updateTabTitle=useCallback((tabId:string,newTitle:string)=>{setTabs(prev=>prev.map(t=>t.id===tabId?{...t,title:newTitle}:t))},[])
//Request brand switch (returns promise that resolves when user confirms/cancels)
const requestBrandSwitch=useCallback((newBrand:string):Promise<boolean>=>{
return new Promise(resolve=>{if(dirtyCount>0){brandSwitchResolveRef.current=resolve;setPendingClose({type:'brand-switch',newBrand})}else{resolve(true)}})},[dirtyCount])
//Handle confirm/cancel dialog actions
const confirmClose=useCallback(()=>{if(!pendingClose)return
if(pendingClose.type==='single'){closeTab(pendingClose.tabId)}
else if(pendingClose.type==='all'){closeAllTabs()}
else if(pendingClose.type==='others'){closeOtherTabs(pendingClose.keepTabId)}
else if(pendingClose.type==='brand-switch'){closeAllTabs();selectBrand(pendingClose.newBrand);brandSwitchResolveRef.current?.(true);brandSwitchResolveRef.current=null}
setPendingClose(null)},[pendingClose,closeTab,closeAllTabs,closeOtherTabs,selectBrand])
const cancelClose=useCallback(()=>{if(pendingClose?.type==='brand-switch'){brandSwitchResolveRef.current?.(false);brandSwitchResolveRef.current=null}
setPendingClose(null)},[pendingClose])
//Get dialog message based on pending action
const getDialogContent=()=>{if(!pendingClose)return{title:'',desc:''}
if(pendingClose.type==='single')return{title:'Unsaved Changes',desc:'This tab has unsaved changes. Discard them?'}
if(pendingClose.type==='all')return{title:'Unsaved Changes',desc:`${dirtyCount} tab${dirtyCount>1?'s have':' has'} unsaved changes. Discard all?`}
if(pendingClose.type==='others'){const otherIds=tabs.filter(t=>t.id!==pendingClose.keepTabId).map(t=>t.id);const cnt=getDirtyCountFor(otherIds)
return{title:'Unsaved Changes',desc:`${cnt} tab${cnt>1?'s have':' has'} unsaved changes. Discard them?`}}
if(pendingClose.type==='brand-switch')return{title:'Unsaved Changes',desc:`${dirtyCount} tab${dirtyCount>1?'s have':' has'} unsaved changes. Discard and switch brand?`}
return{title:'',desc:''}}
const{title,desc}=getDialogContent()
return(<TabContext.Provider value={{tabs,activeTabId,openTab,closeTab,requestCloseTab,closeAllTabs,requestCloseAllTabs,closeOtherTabs,requestCloseOtherTabs,setActiveTab:setActiveTabId,setTabDirty,updateTabTitle,requestBrandSwitch}}>
{children}
<AlertDialog open={!!pendingClose} onOpenChange={open=>{if(!open)cancelClose()}}>
<AlertDialogContent><AlertDialogHeader><AlertDialogTitle>{title}</AlertDialogTitle><AlertDialogDescription>{desc}</AlertDialogDescription></AlertDialogHeader>
<AlertDialogFooter><AlertDialogCancel onClick={cancelClose}>Cancel</AlertDialogCancel><AlertDialogAction onClick={confirmClose}>Discard</AlertDialogAction></AlertDialogFooter>
</AlertDialogContent></AlertDialog>
</TabContext.Provider>)}
export function useTabs(){const ctx=useContext(TabContext);if(!ctx)throw new Error('useTabs must be used within TabProvider');return ctx}
