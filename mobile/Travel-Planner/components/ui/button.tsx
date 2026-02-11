import React from 'react';
import { TouchableOpacity, Text, ActivityIndicator } from 'react-native';

interface ButtonProps {
  onPress?: () => void;
  children: React.ReactNode;
  variant?: 'default' | 'outline' | 'ghost' | 'destructive';
  size?: 'default' | 'sm' | 'lg';
  disabled?: boolean;
  loading?: boolean;
  className?: string;
}

export function Button({
  onPress,
  children,
  variant = 'default',
  size = 'default',
  disabled = false,
  loading = false,
  className = '',
}: ButtonProps) {
  const sizeClasses = {
    default: 'py-3 px-4',
    sm: 'py-2 px-3',
    lg: 'py-4 px-6',
  };

  const variantClasses = {
    default: 'bg-blue-600',
    outline: 'bg-transparent border border-slate-200',
    ghost: 'bg-transparent',
    destructive: 'bg-red-500',
  };

  const textSizeClasses = {
    default: 'text-base',
    sm: 'text-sm',
    lg: 'text-lg',
  };

  const textVariantClasses = {
    default: 'text-white',
    outline: 'text-slate-900',
    ghost: 'text-slate-900',
    destructive: 'text-white',
  };

  return (
    <TouchableOpacity
      onPress={onPress}
      disabled={disabled || loading}
      className={`rounded-xl items-center justify-center flex-row ${sizeClasses[size]} ${variantClasses[variant]} ${disabled ? 'opacity-50' : ''} ${className}`}
      activeOpacity={0.7}
    >
      {loading ? (
        <ActivityIndicator
          color={
            variant === 'default' || variant === 'destructive'
              ? '#FFFFFF'
              : '#0066FF'
          }
        />
      ) : (
        <Text
          className={`font-semibold ${textSizeClasses[size]} ${textVariantClasses[variant]}`}
        >
          {children}
        </Text>
      )}
    </TouchableOpacity>
  );
}
