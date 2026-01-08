//EventBus for backend push events via PyWebView evaluate_js
//Backend calls window.__eventName(data) - we allow multiple subscribers
type EventCallback<T=unknown>=(data:T)=>void
type Unsubscribe=()=>void
class EventBusClass{
private listeners:Map<string,Set<EventCallback>>=new Map()
subscribe<T=unknown>(event:string,cb:EventCallback<T>):Unsubscribe{
if(!this.listeners.has(event))this.listeners.set(event,new Set())
const set=this.listeners.get(event)!
set.add(cb as EventCallback)
return()=>{set.delete(cb as EventCallback)}}
emit<T=unknown>(event:string,data:T):void{
const set=this.listeners.get(event)
if(set)set.forEach(cb=>cb(data))}
//Register global window handler for an event (call once at app init)
registerGlobalHandler(event:string):void{
const globalName=`__${event}`
if(typeof window!=='undefined'&&!(globalName in window)){
(window as unknown as Record<string,unknown>)[globalName]=(data:unknown)=>this.emit(event,data)}}}
//Singleton instance
export const eventBus=new EventBusClass()
//Event names as constants (match backend state.py _push_event calls)
export const EVENT_NAMES={
//Todo events
onTodoListCreated:'onTodoListCreated',
onTodoItemUpdated:'onTodoItemUpdated',
onTodoItemAdded:'onTodoItemAdded',
//Approval events
onApprovalRequest:'onApprovalRequest',
onApprovalCleared:'onApprovalCleared',
//Autonomy events
onAutonomyChanged:'onAutonomyChanged',
//Job lifecycle events
onJobPaused:'onJobPaused',
onJobResumed:'onJobResumed',
onJobInterrupted:'onJobInterrupted',
//Thinking steps (existing)
onThinkingStep:'onThinkingStep',
//Quick generate events
onQuickGenerateProgress:'onQuickGenerateProgress',
onQuickGenerateResult:'onQuickGenerateResult',
onQuickGenerateError:'onQuickGenerateError',
} as const
export type EventName=typeof EVENT_NAMES[keyof typeof EVENT_NAMES]
//Initialize all global handlers (call once in App.tsx)
export function initEventHandlers():void{
Object.values(EVENT_NAMES).forEach(name=>eventBus.registerGlobalHandler(name))}
