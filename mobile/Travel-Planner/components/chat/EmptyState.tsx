import React from 'react';
import { View, Text } from 'react-native';
import { useTheme } from '@/contexts/ThemeContext';

export function EmptyState() {
  const { colors } = useTheme();

  return (
    <View className='flex-1 items-center justify-center'>
      <Text
        className='text-xl font-bold mb-2'
        style={{ color: colors.foreground }}
      >
        Bắt đầu cuộc trò chuyện
      </Text>
      <Text
        className='text-base text-center px-8'
        style={{ color: colors.mutedForeground }}
      >
        Hỏi tôi về kế hoạch du lịch của bạn!{'\n'}
        Ví dụ: &quot;Tôi muốn đi Đà Lạt 3 ngày&quot;
      </Text>
    </View>
  );
}
