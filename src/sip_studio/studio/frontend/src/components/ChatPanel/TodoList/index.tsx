//TodoList component - displays todo list with items and controls
import type{TodoListData}from'@/lib/types/todo'
import{TodoItem}from'./TodoItem'
import{TodoControls}from'./TodoControls'
import'./TodoList.css'
interface TodoListProps{
  todoList:TodoListData
  isPaused:boolean
  onPause:()=>void
  onResume:()=>void
  onStop:()=>void
  onNewDirection:(msg:string)=>void
}
export function TodoList({todoList,isPaused,onPause,onResume,onStop,onNewDirection}:TodoListProps){
  const doneCount=todoList.items.filter(i=>i.status==='done').length
  const total=todoList.items.length
  const isCompleted=!!todoList.completedAt
  const isInterrupted=!!todoList.interruptedAt
  //Show controls if not completed AND not interrupted (pause is OK - not interrupted)
  const showControls=!isCompleted&&!isInterrupted
  const cls=['todo-list']
  if(isCompleted)cls.push('todo-list--completed')
  if(isInterrupted)cls.push('todo-list--interrupted')
  if(isPaused)cls.push('todo-list--paused')
  return(
    <div className={cls.join(' ')}>
      <div className="todo-header">
        <span className="todo-title">{todoList.title}</span>
        <span className="todo-progress">{doneCount}/{total}</span>
        {isCompleted&&<span className="todo-badge">Complete</span>}
        {isInterrupted&&<span className="todo-badge todo-badge--warning">Stopped</span>}
        {isPaused&&!isInterrupted&&<span className="todo-badge todo-badge--info">Paused</span>}
      </div>
      <div className="todo-items">
        {todoList.items.map(item=><TodoItem key={item.id} item={item}/>)}
      </div>
      {showControls&&(
        <TodoControls isPaused={isPaused} onPause={onPause} onResume={onResume} onStop={onStop} onNewDirection={onNewDirection}/>
      )}
    </div>
  )
}
