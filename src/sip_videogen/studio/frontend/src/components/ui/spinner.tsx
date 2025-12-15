import { LoaderCircleIcon, type LucideProps } from 'lucide-react';
import { cn } from '@/lib/utils';

export type SpinnerProps = LucideProps & {
  variant?: 'default' | 'circle';
};

export const Spinner = ({ variant = 'circle', className, ...props }: SpinnerProps) => {
  return (
    <LoaderCircleIcon
      className={cn('animate-spin', className)}
      {...props}
    />
  );
};
