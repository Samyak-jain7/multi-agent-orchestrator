import { cn } from '@/lib/utils';
import { CSSProperties } from 'react';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  style?: CSSProperties;
}

export function Card({ children, className, style }: CardProps) {
  return (
    <div className={cn('card', className)} style={style}>
      {children}
    </div>
  );
}

export function CardHeader({ children, className, style }: CardProps) {
  return (
    <div className={cn('card-header', className)} style={style}>
      {children}
    </div>
  );
}

export function CardTitle({ children, className, style }: CardProps) {
  return (
    <h3 className={cn('card-title', className)} style={style}>
      {children}
    </h3>
  );
}

export function CardDescription({ children, className, style }: CardProps) {
  return (
    <p className={cn('card-description', className)} style={style}>
      {children}
    </p>
  );
}

export function CardContent({ children, className, style }: CardProps) {
  return <div className={cn('card-content', className)} style={style}>{children}</div>;
}

export function CardFooter({ children, className, style }: CardProps) {
  return (
    <div className={cn('card-footer', className)} style={style}>
      {children}
    </div>
  );
}
