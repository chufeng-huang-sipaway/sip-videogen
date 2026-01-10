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
  const doneCount = todoList.items.filter(i => i.status === 'done').length
  const total = todoList.items.length
  const isCompleted = !!todoList.completedAt
  const isInterrupted = !!todoList.interruptedAt

  // Show controls if not completed AND not interrupted (pause is OK - not interrupted)
  const showControls = !isCompleted && !isInterrupted

  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-2xl border border-white/20 shadow-xl transition-all max-w-md w-full",
        "bg-background/80 backdrop-blur-md",
        isCompleted && "opacity-80 grayscale-[0.5]",
        isInterrupted && "border-warning/50 bg-warning/5"
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-white/10 p-4">
        <div className="flex flex-col gap-0.5">
          <h3 className="text-sm font-semibold leading-none tracking-tight text-foreground">
            {todoList.title}
          </h3>
          <span className="text-[11px] text-muted-foreground">
            {doneCount} of {total} items completed
          </span>
        </div>

        <div className="flex items-center gap-2">
          {isCompleted && (
            <span className="inline-flex items-center rounded-full bg-success/10 px-3 py-1 text-xs font-medium text-success ring-1 ring-inset ring-success/20">
              Complete
            </span>
          )}
          {isInterrupted && (
            <span className="inline-flex items-center rounded-full bg-warning/10 px-3 py-1 text-xs font-medium text-warning ring-1 ring-inset ring-warning/20">
              Stopped
            </span>
          )}
          {isPaused && !isInterrupted && (
            <span className="inline-flex items-center rounded-full bg-brand-500/10 px-3 py-1 text-xs font-medium text-brand-500 ring-1 ring-inset ring-brand-500/20">
              Paused
            </span>
          )}
          {!isCompleted && !isInterrupted && !isPaused && (
            <span className="inline-flex items-center rounded-full bg-brand-500/10 px-3 py-1 text-xs font-medium text-brand-500 ring-1 ring-inset ring-brand-500/20">
              In Progress
            </span>
          )}
        </div>
      </div>

      {/* Items */}
      <div className="flex flex-col gap-3 p-4">
        {todoList.items.map(item => (
          <TodoItem key={item.id} item={item} />
        ))}
      </div>

      {/* Controls */}
      {showControls && (
        <div className="px-4 pb-4">
          <TodoControls
            onStop={onStop}
          />
        </div>
      )}
    </div>
  )
}
