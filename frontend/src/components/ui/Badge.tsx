import { cn } from '@/lib/utils';
import { CSSProperties, MouseEventHandler } from 'react';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'default' | 'secondary' | 'outline';
  className?: string;
  style?: CSSProperties;
  onClick?: MouseEventHandler<HTMLSpanElement>;
}

export function Badge({ children, variant = 'default', className, style, onClick }: BadgeProps) {
  return (
    <span
      className={cn('badge', `badge-${variant}`, className)}
      style={style}
      onClick={onClick}
    >
      {children}
    </span>
  );
}
