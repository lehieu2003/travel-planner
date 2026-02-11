import React from 'react';
import { View, Text, ScrollView, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { User as UserIcon, Mail, Calendar } from 'lucide-react-native';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';

export default function ProfileScreen() {
  const router = useRouter();
  const { user, logout } = useAuth();

  const handleLogout = () => {
    Alert.alert('Đăng xuất', 'Bạn có chắc chắn muốn đăng xuất?', [
      { text: 'Hủy', style: 'cancel' },
      {
        text: 'Đăng xuất',
        style: 'destructive',
        onPress: async () => {
          await logout();
          router.replace('/login' as any);
        },
      },
    ]);
  };

  return (
    <SafeAreaView className='flex-1 bg-slate-50' edges={['top']}>
      <View className='px-4 py-4 bg-white border-b border-slate-200'>
        <Text className='text-2xl font-bold text-slate-900'>Hồ sơ cá nhân</Text>
      </View>

      <ScrollView className='flex-1'>
        <View className='bg-white items-center py-8 mt-4 mx-4 rounded-2xl border border-slate-200'>
          <View className='w-20 h-20 rounded-full bg-blue-600 items-center justify-center mb-4'>
            <UserIcon size={40} color='#FFFFFF' />
          </View>

          <Text className='text-xl font-bold text-slate-900 mb-1'>
            {user?.full_name || 'Người dùng'}
          </Text>
          <Text className='text-sm text-slate-600'>{user?.email}</Text>
        </View>

        <View className='p-4'>
          <Text className='text-base font-semibold text-slate-900 mb-3'>
            Thông tin tài khoản
          </Text>

          <View className='bg-white rounded-xl border border-slate-200 p-4'>
            <View className='flex-row items-center'>
              <View className='w-10 h-10 rounded-full bg-blue-50 items-center justify-center mr-3'>
                <Mail size={20} color='#0066FF' />
              </View>
              <View className='flex-1'>
                <Text className='text-xs text-slate-600 mb-0.5'>Email</Text>
                <Text className='text-base font-semibold text-slate-900'>
                  {user?.email}
                </Text>
              </View>
            </View>

            <View className='h-px bg-slate-200 my-4' />

            <View className='flex-row items-center'>
              <View className='w-10 h-10 rounded-full bg-blue-50 items-center justify-center mr-3'>
                <Calendar size={20} color='#0066FF' />
              </View>
              <View className='flex-1'>
                <Text className='text-xs text-slate-600 mb-0.5'>
                  Thành viên từ
                </Text>
                <Text className='text-base font-semibold text-slate-900'>
                  {new Date().toLocaleDateString('vi-VN')}
                </Text>
              </View>
            </View>
          </View>
        </View>

        <View className='p-4'>
          <Button variant='destructive' onPress={handleLogout} className='mt-2'>
            Đăng xuất
          </Button>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
