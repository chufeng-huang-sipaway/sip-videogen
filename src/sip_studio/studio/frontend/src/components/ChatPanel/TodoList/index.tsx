//TodoList component - displays todo list with items and controls
import type { TodoListData } from '@/lib/types/todo'
import { TodoItem } from './TodoItem'
import { TodoControls } from './TodoControls'
import { cn } from '@/lib/utils'
interface TodoListProps {
  todoList: TodoListData
  isPaused: boolean
  onPause: () => void
  onResume: () => void
  onStop: () => void
  onNewDirection: (msg: string) => void
}
export function TodoList({ todoList, isPaused, onStop }: TodoListProps) {
  const done = todoList.items.filter(i => i.status === 'done').length
  const total = todoList.items.length
  const isCompleted = !!todoList.completedAt
  const isInterrupted = !!todoList.interruptedAt
  const showControls = !isCompleted && !isInterrupted
  return (
    <div className={cn(
      "relative overflow-hidden rounded-xl border border-border/50 shadow-md transition-all w-full",
      "bg-background/90 backdrop-blur-sm",
      isCompleted && "opacity-75",
      isInterrupted && "border-warning/40"
    )}>
      {/* Header */}
      <div className="flex flex-col gap-2 px-4 pt-3 pb-2">
        <div className="flex items-center justify-between">
          <h3 className="text-[13px] font-semibold leading-tight text-foreground">{todoList.title}</h3>
          {isCompleted && <span className="inline-flex items-center rounded-full bg-success/10 px-2 py-0.5 text-[10px] font-medium text-success">Done</span>}
          {isInterrupted && <span className="inline-flex items-center rounded-full bg-warning/10 px-2 py-0.5 text-[10px] font-medium text-warning">Stopped</span>}
          {isPaused && !isInterrupted && <span className="inline-flex items-center rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground">Paused</span>}
          {!isCompleted && !isInterrupted && !isPaused && <span className="inline-flex items-center rounded-full bg-progress/10 px-2 py-0.5 text-[10px] font-medium text-progress">Working</span>}
        </div>
        <div className="w-full h-1 bg-muted rounded-full overflow-hidden">
          <div className="h-full bg-success rounded-full transition-all duration-500" style={{ width: `${total > 0 ? (done / total) * 100 : 0}%` }} />
        </div>
      </div>
      {/* Items */}
      <div className="flex flex-col gap-2 px-4 pb-3">
        {todoList.items.map(item => <TodoItem key={item.id} item={item} />)}
      </div>
      {/* Controls */}
      {showControls && (
        <div className="px-4 pb-3">
          <TodoControls onStop={onStop} />
        </div>
      )}
    </div>
  )
}
