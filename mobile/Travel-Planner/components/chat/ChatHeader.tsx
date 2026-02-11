import React from 'react';
import { View, Text, TouchableOpacity } from 'react-native';
import { Menu, Plus } from 'lucide-react-native';

interface ChatHeaderProps {
  conversationTitle?: string;
  onShowConversations: () => void;
  onNewConversation: () => void;
}

export function ChatHeader({
  conversationTitle,
  onShowConversations,
  onNewConversation,
}: ChatHeaderProps) {
  return (
    <View className='flex-row items-center justify-between px-4 py-3 bg-white border-b border-slate-200'>
      <TouchableOpacity
        onPress={onShowConversations}
        className='w-10 h-10 rounded-xl items-center justify-center'
        activeOpacity={0.7}
      >
        <Menu size={24} color='#1E293B' />
      </TouchableOpacity>

      <View className='flex-1 items-center px-4'>
        <Text className='text-lg font-bold text-slate-900' numberOfLines={1}>
          {conversationTitle || 'Travel Planner AI'}
        </Text>
      </View>

      <TouchableOpacity
        onPress={onNewConversation}
        className='w-10 h-10 rounded-full bg-blue-50 items-center justify-center'
        activeOpacity={0.7}
      >
        <Plus size={20} color='#0066FF' />
      </TouchableOpacity>
    </View>
  );
}
