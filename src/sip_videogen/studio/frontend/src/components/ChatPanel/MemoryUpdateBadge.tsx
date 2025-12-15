import { Brain } from 'lucide-react'

interface Props {
  message: string
}

export function MemoryUpdateBadge({ message }: Props) {
  return (
    <div className="flex items-center gap-2 mt-2 p-2 bg-purple-50 dark:bg-purple-900/20 rounded-lg text-sm">
      <Brain className="h-4 w-4 text-purple-500 flex-shrink-0" />
      <span className="text-purple-700 dark:text-purple-300">{message}</span>
    </div>
  )
}
