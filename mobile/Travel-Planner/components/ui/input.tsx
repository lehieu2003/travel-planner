import React from 'react';
import { TextInput, View, Text, TextInputProps } from 'react-native';
import { useTheme } from '@/contexts/ThemeContext';

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
  const { colors } = useTheme();

  return (
    <View className={`mb-4 ${containerClassName}`}>
      {label && (
        <Text
          className='text-sm font-semibold mb-2'
          style={{ color: colors.foreground }}
        >
          {label}
        </Text>
      )}
      <TextInput
        className={`border rounded-xl px-4 py-3 text-base ${className}`}
        style={{
          color: colors.foreground,
          backgroundColor: colors.card,
          borderColor: error ? '#EF4444' : colors.border,
        }}
        placeholderTextColor={colors.mutedForeground}
        {...props}
      />
      {error && (
        <Text className='text-xs mt-1' style={{ color: '#EF4444' }}>
          {error}
        </Text>
      )}
    </View>
  );
}
