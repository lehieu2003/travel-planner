import React from 'react';
import { TextInput, View, Text, TextInputProps } from 'react-native';

interface InputProps extends TextInputProps {
  label?: string;
  error?: string;
  containerClassName?: string;
}

export function Input({
  label,
  error,
  containerClassName = '',
  className = '',
  ...props
}: InputProps) {
  return (
    <View className={`mb-4 ${containerClassName}`}>
      {label && (
        <Text className='text-sm font-semibold text-slate-900 mb-2'>
          {label}
        </Text>
      )}
      <TextInput
        className={`border rounded-xl px-4 py-3 text-base text-slate-900 bg-white ${error ? 'border-red-500' : 'border-slate-200'} ${className}`}
        placeholderTextColor='#94A3B8'
        {...props}
      />
      {error && <Text className='text-red-500 text-xs mt-1'>{error}</Text>}
    </View>
  );
}
