import { cn } from '@/lib/utils'

export type ActivityType = 'thinking' | 'tool_start' | 'tool_end' | 'skill_loaded' | ''

interface ActivityIndicatorProps {
  type: ActivityType
  message: string
  skills?: string[]
  className?: string
}

/**
 * Get the indicator color class based on activity type.
 * - thinking: sky blue
 * - tool_start: emerald green
 * - skill_loaded: amber
 * - default: gray
 */
const getIndicatorColorClass = (type: ActivityType): string => {
  switch (type) {
    case 'thinking':
      return 'bg-sky-500'
    case 'tool_start':
      return 'bg-emerald-500'
    case 'skill_loaded':
      return 'bg-amber-500'
    default:
      return 'bg-gray-400'
  }
}

/**
 * Get the ping animation color class based on activity type.
 */
const getPingColorClass = (type: ActivityType): string => {
  switch (type) {
    case 'thinking':
      return 'bg-sky-400'
    case 'tool_start':
      return 'bg-emerald-400'
    case 'skill_loaded':
      return 'bg-amber-400'
    default:
      return 'bg-gray-300'
  }
}

/**
 * Get the text color class based on activity type.
 */
const getTextColorClass = (type: ActivityType): string => {
  switch (type) {
    case 'thinking':
      return 'text-sky-700 dark:text-sky-300'
    case 'tool_start':
      return 'text-emerald-700 dark:text-emerald-300'
    case 'skill_loaded':
      return 'text-amber-700 dark:text-amber-300'
    default:
      return 'text-gray-600 dark:text-gray-400'
  }
}

/**
 * Pulsing indicator dot that shows different colors based on activity type.
 */
function PulsingIndicator({ type }: { type: ActivityType }) {
  return (
    <span className="relative flex h-2.5 w-2.5">
      {/* Ping animation layer */}
      <span
        className={cn(
          'absolute inline-flex h-full w-full animate-ping rounded-full opacity-75',
          getPingColorClass(type)
        )}
      />
      {/* Solid dot layer */}
      <span
        className={cn(
          'relative inline-flex h-2.5 w-2.5 rounded-full',
          getIndicatorColorClass(type)
        )}
      />
    </span>
  )
}

/**
 * Activity indicator component that shows the current agent activity
 * with a pulsing colored dot and status message.
 */
export function ActivityIndicator({ type, message, skills, className }: ActivityIndicatorProps) {
  const hasSkills = skills && skills.length > 0

  return (
    <div className={cn('flex flex-col gap-1', className)}>
      {/* Show loaded skills */}
      {hasSkills && (
        <div className="flex flex-wrap gap-1.5 mb-1">
          {skills.map((skill) => (
            <span
              key={skill}
              className={cn(
                'inline-flex items-center gap-1.5 rounded-full',
                'bg-amber-100/80 dark:bg-amber-900/30',
                'px-2 py-0.5',
                'text-xs font-medium text-amber-700 dark:text-amber-300'
              )}
            >
              <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
              {skill}
            </span>
          ))}
        </div>
      )}

      {/* Current activity */}
      <div
        className={cn(
          'inline-flex items-center gap-2.5 rounded-full',
          'bg-gray-100/80 dark:bg-gray-800/80',
          'px-3 py-1.5',
          'transition-all duration-200'
        )}
      >
        <PulsingIndicator type={type} />
        <span className={cn('text-sm font-medium', getTextColorClass(type))}>
          {message || 'Working...'}
        </span>
      </div>
    </div>
  )
}
