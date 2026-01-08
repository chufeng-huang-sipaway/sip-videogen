//TodoItem component - displays single todo item with status and outputs
import type{TodoItemData}from'@/lib/types/todo'
import'./TodoList.css'
const statusIcons:{[k:string]:string}={pending:'\u25cb',in_progress:'\u25d0',done:'\u25cf',error:'\u2715',paused:'\u23f8'}
interface TodoItemProps{item:TodoItemData}
export function TodoItem({item}:TodoItemProps){
  const icon=statusIcons[item.status]||'\u25cb'
  return(
    <div className={`todo-item todo-item--${item.status}`}>
      <span className="todo-status">{icon}</span>
      <span className="todo-description">{item.description}</span>
      {item.outputs&&item.outputs.length>0&&(
        <div className="todo-outputs">
          {item.outputs.map((o,i)=>(
            <img key={i} src={o.data||o.path} className="todo-output-thumb" alt={`Output ${i+1}`}/>
          ))}
        </div>
      )}
      {item.error&&<span className="todo-error">{item.error}</span>}
    </div>
  )
}
