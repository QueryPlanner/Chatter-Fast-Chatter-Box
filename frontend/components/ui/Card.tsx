import React from 'react';
import { cn } from '@/lib/utils';

export type CardProps = React.HTMLAttributes<HTMLDivElement>;

export function Card({ className, ...props }: CardProps) {
  return (
    <div
      className={cn("bg-surface rounded-lg p-8 border border-border-dark", className)}
      {...props}
    />
  );
}