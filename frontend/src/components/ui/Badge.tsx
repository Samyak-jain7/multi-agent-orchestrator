import { cn } from '@/lib/utils';
import { CSSProperties } from 'react';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'default' | 'secondary' | 'outline';
  className?: string;
  style?: CSSProperties;
}

export function Badge({ children, variant = 'default', className, style }: BadgeProps) {
  return (
    <span
      className={cn('badge', `badge-${variant}`, className)}
      style={style}
    >
      {children}
    </span>
  );
}
