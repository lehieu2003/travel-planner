import React from 'react';
import { View, TextInput, TouchableOpacity } from 'react-native';
import { Send } from 'lucide-react-native';

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
  return (
    <View className='flex-row items-end px-4 py-3 bg-white border-t border-slate-200'>
      <TextInput
        className='flex-1 max-h-24 px-4 py-3 bg-slate-50 rounded-3xl text-base text-slate-900 mr-3'
        value={value}
        onChangeText={onChangeText}
        placeholder='Nhập tin nhắn...'
        placeholderTextColor='#94A3B8'
        multiline
        maxLength={500}
        editable={!disabled}
      />
      <TouchableOpacity
        className={`w-11 h-11 rounded-full bg-blue-600 items-center justify-center ${
          !value.trim() || disabled ? 'opacity-50' : ''
        }`}
        onPress={onSend}
        disabled={!value.trim() || disabled}
      >
        <Send size={20} color='#FFFFFF' />
      </TouchableOpacity>
    </View>
  );
}
