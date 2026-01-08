//useTodo hook - manages todo list state from backend push events
import{useState,useEffect,useCallback}from'react'
import{eventBus,EVENT_NAMES}from'@/lib/eventBus'
import type{TodoList,TodoItemStatus,TodoListCreatedEvent,TodoItemUpdatedEvent,TodoItemAddedEvent,TodoProgress}from'@/types/todo'
import{getTodoProgress}from'@/types/todo'
interface UseTodoResult{
todoList:TodoList|null
progress:TodoProgress
//Control actions (delegate to bridge)
skipItem:(itemId:string)=>void
cancelAllPending:()=>void
}
interface UseTodoOptions{
onSkipItem?:(itemId:string)=>Promise<void>
onCancelAllPending?:()=>Promise<void>}
export function useTodo(runId:string|null,options?:UseTodoOptions):UseTodoResult{
const[todoList,setTodoList]=useState<TodoList|null>(null)
//Subscribe to todo events
useEffect(()=>{
if(!runId)return
const unsubs:Array<()=>void>=[]
//Todo list created
unsubs.push(eventBus.subscribe<TodoListCreatedEvent>(EVENT_NAMES.onTodoListCreated,(data)=>{
if(data.runId===runId)setTodoList(data)}))
//Item updated
unsubs.push(eventBus.subscribe<TodoItemUpdatedEvent>(EVENT_NAMES.onTodoItemUpdated,(data)=>{
if(data.runId!==runId)return
setTodoList(prev=>{
if(!prev)return prev
const items=prev.items.map(it=>it.id===data.itemId?{...it,status:data.status as TodoItemStatus,outputs:data.outputs??it.outputs,error:data.error??it.error,updatedAt:new Date().toISOString()}:it)
return{...prev,items,updatedAt:new Date().toISOString()}})}))
//Item added
unsubs.push(eventBus.subscribe<TodoItemAddedEvent>(EVENT_NAMES.onTodoItemAdded,(data)=>{
if(data.runId!==runId)return
setTodoList(prev=>{
if(!prev)return prev
return{...prev,items:[...prev.items,data.item],updatedAt:new Date().toISOString()}})}))
return()=>unsubs.forEach(u=>u())
},[runId])
//Clear when runId changes to null
useEffect(()=>{if(!runId)setTodoList(null)},[runId])
const skipItem=useCallback((itemId:string)=>{options?.onSkipItem?.(itemId).catch(()=>{})},[options])
const cancelAllPending=useCallback(()=>{options?.onCancelAllPending?.().catch(()=>{})},[options])
return{todoList,progress:getTodoProgress(todoList),skipItem,cancelAllPending}
}
