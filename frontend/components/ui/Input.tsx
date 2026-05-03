import React from 'react';
import { cn } from '@/lib/utils';

export type InputProps = React.InputHTMLAttributes<HTMLInputElement>;

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, ...props }, ref) => {
    return (
      <input
        ref={ref}
        className={cn(
          "bg-surface border border-border-dark rounded-md p-3 w-full outline-none focus:border-primary",
          className
        )}
        {...props}
      />
    );
  }
);

Input.displayName = 'Input';