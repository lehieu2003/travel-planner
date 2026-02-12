import React from 'react';
import { View, Text, TouchableOpacity } from 'react-native';
import { Menu, Plus } from 'lucide-react-native';
import { useTheme } from '@/contexts/ThemeContext';

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
  const { colors } = useTheme();

  return (
    <View
      className='flex-row items-center justify-between px-4 py-3 border-b'
      style={{ backgroundColor: colors.card, borderColor: colors.border }}
    >
      <TouchableOpacity
        onPress={() => {
          onShowConversations();
        }}
        className='w-10 h-10 rounded-xl items-center justify-center'
        activeOpacity={0.7}
      >
        <Menu size={24} color={colors.foreground} />
      </TouchableOpacity>

      <View className='flex-1 items-center px-4'>
        <Text
          className='text-lg font-bold'
          numberOfLines={1}
          style={{ color: colors.foreground }}
        >
          {conversationTitle || 'Travel Planner AI'}
        </Text>
      </View>

      <TouchableOpacity
        onPress={onNewConversation}
        className='w-10 h-10 rounded-full items-center justify-center'
        style={{ backgroundColor: colors.accent }}
        activeOpacity={0.7}
      >
        <Plus size={20} color={colors.primary} />
      </TouchableOpacity>
    </View>
  );
}
