//Todo types matching backend job_state.py models (camelCase from serialization_alias)
export type TodoItemStatus='pending'|'in_progress'|'done'|'error'|'paused'|'cancelled'|'skipped'
export const TERMINAL_STATUSES:TodoItemStatus[]=['done','error','cancelled','skipped']
export function isTerminalStatus(s:TodoItemStatus):boolean{return TERMINAL_STATUSES.includes(s)}
export interface TodoItem{
id:string
description:string
status:TodoItemStatus
outputs:string[]
error:string|null
createdAt:string
updatedAt:string}
export interface TodoList{
id:string
runId:string
title:string
items:TodoItem[]
createdAt:string
updatedAt:string}
export interface TodoProgress{done:number;total:number}
export function getTodoProgress(list:TodoList|null):TodoProgress{
if(!list)return{done:0,total:0}
const done=list.items.filter(i=>isTerminalStatus(i.status)).length
return{done,total:list.items.length}}
//Event payloads (from state.py _push_event calls)
export interface TodoListCreatedEvent extends TodoList{}
export interface TodoItemUpdatedEvent{
runId:string
itemId:string
status:TodoItemStatus
outputs:string[]|null
error:string|null}
export interface TodoItemAddedEvent{
runId:string
item:TodoItem}
