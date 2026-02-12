import React from 'react';
import { View, TextInput, TouchableOpacity } from 'react-native';
import { Send } from 'lucide-react-native';
import { useTheme } from '@/contexts/ThemeContext';

interface ChatInputProps {
  value: string;
  onChangeText: (text: string) => void;
  onSend: () => void;
  disabled?: boolean;
}

export function ChatInput({
  value,
  onChangeText,
  onSend,
  disabled,
}: ChatInputProps) {
  const { colors } = useTheme();

  return (
    <View
      className='flex-row items-end px-4 py-3 border-t'
      style={{ backgroundColor: colors.card, borderColor: colors.border }}
    >
      <TextInput
        className='flex-1 max-h-24 px-4 py-3 rounded-3xl text-base mr-3'
        style={{ backgroundColor: colors.input, color: colors.foreground }}
        value={value}
        onChangeText={onChangeText}
        placeholder='Nhập tin nhắn...'
        placeholderTextColor={colors.mutedForeground}
        multiline
        maxLength={500}
        editable={!disabled}
      />
      <TouchableOpacity
        className={`w-11 h-11 rounded-full items-center justify-center ${
          !value.trim() || disabled ? 'opacity-50' : ''
        }`}
        style={{ backgroundColor: colors.primary }}
        onPress={onSend}
        disabled={!value.trim() || disabled}
      >
        <Send size={20} color='#FFFFFF' />
      </TouchableOpacity>
    </View>
  );
}
