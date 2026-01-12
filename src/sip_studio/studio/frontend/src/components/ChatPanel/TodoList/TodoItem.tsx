//TodoItem component - displays single todo item with status
import { Check, Circle, Loader2, AlertCircle, PauseCircle } from 'lucide-react'
import type { TodoItemData } from '@/lib/types/todo'
import { cn } from '@/lib/utils'
interface TodoItemProps { item: TodoItemData }
export function TodoItem({ item }: TodoItemProps) {
  const isPending = item.status === 'pending'
  const isInProgress = item.status === 'in_progress'
  const isDone = item.status === 'done'
  const isError = item.status === 'error'
  const isPaused = item.status === 'paused'
  return (
    <div className={cn(
      "group flex items-start gap-2.5 rounded-lg px-2.5 py-2 transition-all",
      isInProgress && "bg-progress/8",
      isError && "bg-destructive/5",
      isPaused && "opacity-60"
    )}>
      <div className="flex h-5 w-5 shrink-0 items-center justify-center">
        {isDone && (
          <div className="flex h-[18px] w-[18px] items-center justify-center rounded-full bg-success text-white">
            <Check className="h-3 w-3" strokeWidth={3} />
          </div>
        )}
        {isInProgress && <Loader2 className="h-4 w-4 animate-spin text-progress" />}
        {isPending && <Circle className="h-4 w-4 text-muted-foreground/25" strokeWidth={1.5} />}
        {isError && <AlertCircle className="h-4 w-4 text-destructive" strokeWidth={2} />}
        {isPaused && <PauseCircle className="h-4 w-4 text-muted-foreground/50" strokeWidth={2} />}
      </div>
      <span className={cn(
        "text-[13px] leading-snug transition-colors",
        isDone && "text-muted-foreground line-through decoration-muted-foreground/30",
        isInProgress && "text-progress font-medium",
        isPending && "text-foreground/80",
        isError && "text-destructive",
        isPaused && "text-muted-foreground"
      )}>{item.description}</span>
    </div>
  )
}
