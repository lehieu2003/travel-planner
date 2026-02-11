import React from 'react';
import { View, Text } from 'react-native';

export function EmptyState() {
  return (
    <View className='flex-1 items-center justify-center'>
      <Text className='text-xl font-bold text-slate-900 mb-2'>
        Bắt đầu cuộc trò chuyện
      </Text>
      <Text className='text-base text-slate-600 text-center px-8'>
        Hỏi tôi về kế hoạch du lịch của bạn!{'\n'}
        Ví dụ: &quot;Tôi muốn đi Đà Lạt 3 ngày&quot;
      </Text>
    </View>
  );
}
