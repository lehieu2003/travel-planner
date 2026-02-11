import React from 'react';
import { View, Text, ScrollView } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

export default function ItinerariesScreen() {
  return (
    <SafeAreaView className='flex-1 bg-slate-50' edges={['top']}>
      <View className='px-4 py-4 bg-white border-b border-slate-200'>
        <Text className='text-2xl font-bold text-slate-900'>
          Lịch trình đã lưu
        </Text>
      </View>

      <ScrollView className='flex-1'>
        <View className='flex-1 items-center justify-center py-24'>
          <Text className='text-6xl mb-4'>📋</Text>
          <Text className='text-lg font-semibold text-slate-900 mb-2'>
            Chưa có lịch trình nào
          </Text>
          <Text className='text-sm text-slate-600 text-center'>
            Lưu lịch trình từ cuộc trò chuyện để xem ở đây
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
