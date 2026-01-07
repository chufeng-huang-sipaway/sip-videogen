import { useState, useEffect, useCallback } from 'react'
import { X, CheckCircle2, AlertCircle, Info } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

export type StatusAlertVariant = 'success' | 'error' | 'info'

interface StatusAlertProps {
  /** Alert variant determines styling */
  variant: StatusAlertVariant
  /** Message to display */
  message: string
  /** Optional title for the alert */
  title?: string
  /** Whether the alert can be dismissed */
  dismissible?: boolean
  /** Callback when alert is dismissed */
  onDismiss?: () => void
  /** Auto-dismiss after X milliseconds (only for success/info, not errors) */
  autoDismissMs?: number
  /** Additional class names */
  className?: string
}

/**
 * StatusAlert - Inline status feedback component for Brand Memory.
 * Features:
 * - Three variants: success (green), error (brand red), info (neutral)
 * - Dismissible option with close button
 * - Auto-dismiss for success/info (errors persist until resolved)
 * - Consistent styling across Brand Memory UI
 * Usage:
 * ```tsx
 * <StatusAlert variant="success" message="Changes saved successfully" dismissible />
 * <StatusAlert variant="error" message="Failed to save changes" />
 * <StatusAlert variant="info" message="AI context refreshed automatically" autoDismissMs={5000} />
 * ```
 */
export function StatusAlert({
  variant,
  message,
  title,
  dismissible = false,
  onDismiss,
  autoDismissMs,
  className,
}: StatusAlertProps) {
  const [isVisible, setIsVisible] = useState(true)

  // Handle dismiss
  const handleDismiss = useCallback(() => {
    setIsVisible(false)
    onDismiss?.()
  }, [onDismiss])

  // Auto-dismiss effect (only for success/info, not errors)
  useEffect(() => {
    if (autoDismissMs && variant !== 'error' && isVisible) {
      const timer = setTimeout(handleDismiss, autoDismissMs)
      return () => clearTimeout(timer)
    }
  }, [autoDismissMs, variant, isVisible, handleDismiss])

  // Don't render if dismissed
  if (!isVisible) {
    return null
  }

  //Get variant-specific styles and icon
  const variantConfig = {
    success: {containerClass:'bg-success-a10 border-success/20',textClass:'text-success',icon:CheckCircle2,iconClass:'text-success'},
    error: {containerClass:'bg-destructive/10 border-destructive/20',textClass:'text-destructive',icon:AlertCircle,iconClass:'text-destructive'},
    info: {containerClass:'bg-muted border-border',textClass:'text-muted-foreground',icon:Info,iconClass:'text-muted-foreground'},
  }

  const config = variantConfig[variant]
  const Icon = config.icon

  return (
    <Alert className={cn(config.containerClass, 'relative', className)}>
      <Icon className={cn('h-4 w-4', config.iconClass)} />
      <AlertDescription className={config.textClass}>
        {title && <span className="font-medium">{title} </span>}
        {message}
      </AlertDescription>
      {dismissible && (
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={handleDismiss}
          className={cn(
            'absolute right-2 top-2 h-6 w-6 p-0 rounded-full',
            'hover:bg-foreground/10',
            config.textClass
          )}
          aria-label="Dismiss"
        >
          <X className="h-3 w-3" />
        </Button>
      )}
    </Alert>
  )
}
