import React from 'react';
import { cn } from '@/lib/utils';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary';
}

export function Button({ className, variant = 'primary', ...props }: ButtonProps) {
  return (
    <button
      className={cn(
        "rounded-md px-6 py-3 font-medium transition-colors",
        variant === 'primary' 
          ? "bg-primary text-surface border border-transparent hover:bg-blue-700" 
          : "bg-surface border border-border-dark text-text-main hover:bg-gray-50",
        className
      )}
      {...props}
    />
  );
}