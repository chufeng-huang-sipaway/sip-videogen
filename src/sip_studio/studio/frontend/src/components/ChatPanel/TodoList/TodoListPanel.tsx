//TodoListPanel - Full todo list with header, items, and controls
import{useState}from'react'
import{ChevronDown,ChevronRight,ListTodo}from'lucide-react'
import{Progress}from'@/components/ui/progress'
import{cn}from'@/lib/utils'
import type{TodoList}from'@/types/todo'
import{getTodoProgress}from'@/types/todo'
import{TodoItem}from'./TodoItem'
import{TodoControls}from'./TodoControls'
interface TodoListPanelProps{
todoList:TodoList|null
isPaused:boolean
isGenerating:boolean
onPause:()=>void
onResume:()=>void
onStop:()=>void
onSkipItem?:(id:string)=>void
className?:string}
export function TodoListPanel({todoList,isPaused,isGenerating,onPause,onResume,onStop,onSkipItem,className}:TodoListPanelProps){
const[expanded,setExpanded]=useState(true)
if(!todoList||todoList.items.length===0)return null
const{done,total}=getTodoProgress(todoList)
const pct=total>0?Math.round((done/total)*100):0
//Auto-collapse when complete
const allDone=done===total&&!isGenerating
return(<div className={cn('border rounded-lg bg-card/50 backdrop-blur-sm overflow-hidden',className)}>
{/*Header*/}
<button type="button" onClick={()=>setExpanded(e=>!e)} className="w-full flex items-center gap-3 px-3 py-2 hover:bg-muted/50 transition-colors">
<ListTodo className="h-4 w-4 text-muted-foreground"/>
<span className="flex-1 text-left text-sm font-medium truncate">{todoList.title||'Tasks'}</span>
<span className="text-xs text-muted-foreground">{done}/{total}</span>
{expanded?<ChevronDown className="h-4 w-4 text-muted-foreground"/>:<ChevronRight className="h-4 w-4 text-muted-foreground"/>}</button>
{/*Progress bar*/}
<Progress value={pct} className="h-1 rounded-none"/>
{/*Expandable content*/}
{expanded&&(<div className="px-3 py-2 space-y-1 max-h-64 overflow-y-auto">
{todoList.items.map(item=><TodoItem key={item.id} item={item} onSkip={onSkipItem} disabled={allDone}/>)}</div>)}
{/*Controls footer*/}
{(isGenerating||isPaused)&&expanded&&(<div className="px-3 py-2 border-t border-border/50">
<TodoControls isPaused={isPaused} isGenerating={isGenerating} onPause={onPause} onResume={onResume} onStop={onStop}/></div>)}</div>)}
