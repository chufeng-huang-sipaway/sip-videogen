import { LoaderCircleIcon, LoaderIcon, type LucideProps } from 'lucide-react'
import { cn } from '@/lib/utils'

export type SpinnerProps = LucideProps & {
  variant?: 'default' | 'circle'
}

export function Spinner({ variant = 'circle', className, ...props }: SpinnerProps) {
  const Icon = variant === 'default' ? LoaderIcon : LoaderCircleIcon
  return <Icon className={cn('animate-spin', className)} {...props} />
}
