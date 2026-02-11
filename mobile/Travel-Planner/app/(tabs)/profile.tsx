import React, { useState, useEffect } from 'react';
import { View, Text, ScrollView, Alert, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import {
  User as UserIcon,
  Mail,
  Calendar,
  MapPin,
  Heart,
  Bookmark,
} from 'lucide-react-native';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { API_ENDPOINTS, getAuthHeaders } from '@/config/api';

interface ProfileData {
  id: number;
  email: string;
  full_name: string | null;
  age: number | null;
  gender: 'male' | 'female' | 'other' | null;
  energy_level: 'low' | 'medium' | 'high' | null;
  budget_min: number | null;
  budget_max: number | null;
  preferences: string[];
  stats?: {
    trips_planned: number;
    places_visited: number;
    saved_itineraries: number;
  };
}

export default function ProfileScreen() {
  const router = useRouter();
  const { user, logout } = useAuth();
  const [profileData, setProfileData] = useState<ProfileData | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(API_ENDPOINTS.PROFILE.GET, {
        headers,
      });

      if (response.ok) {
        const data = await response.json();
        setProfileData(data);
      }
    } catch (error) {
      console.error('Error loading profile:', error);
    } finally {
      setIsLoading(false);
    }
  };

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

  const formatBudget = (min: number | null, max: number | null) => {
    if (!min || !max) return 'Chưa thiết lập';
    return `${(min / 1000000).toFixed(0)} - ${(max / 1000000).toFixed(0)} triệu VNĐ`;
  };

  const getEnergyLevelText = (level: string | null) => {
    const levels: Record<string, string> = {
      low: 'Thư giãn',
      medium: 'Vừa phải',
      high: 'Năng động',
    };
    return level ? levels[level] : 'Chưa thiết lập';
  };

  if (isLoading) {
    return (
      <SafeAreaView className='flex-1 bg-slate-50' edges={['top']}>
        <View className='flex-1 items-center justify-center'>
          <ActivityIndicator size='large' color='#0066FF' />
        </View>
      </SafeAreaView>
    );
  }

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
            {profileData?.full_name || user?.full_name || 'Người dùng'}
          </Text>
          <Text className='text-sm text-slate-600'>
            {profileData?.email || user?.email}
          </Text>
        </View>

        {profileData?.stats && (
          <View className='flex-row px-4 mt-4 gap-3'>
            <View className='flex-1 bg-white rounded-xl border border-slate-200 p-4 items-center'>
              <MapPin size={24} color='#0066FF' />
              <Text className='text-2xl font-bold text-slate-900 mt-2'>
                {profileData.stats.trips_planned}
              </Text>
              <Text className='text-xs text-slate-600 mt-1'>Chuyến đi</Text>
            </View>
            <View className='flex-1 bg-white rounded-xl border border-slate-200 p-4 items-center'>
              <Heart size={24} color='#0066FF' />
              <Text className='text-2xl font-bold text-slate-900 mt-2'>
                {profileData.stats.places_visited}
              </Text>
              <Text className='text-xs text-slate-600 mt-1'>Địa điểm</Text>
            </View>
            <View className='flex-1 bg-white rounded-xl border border-slate-200 p-4 items-center'>
              <Bookmark size={24} color='#0066FF' />
              <Text className='text-2xl font-bold text-slate-900 mt-2'>
                {profileData.stats.saved_itineraries}
              </Text>
              <Text className='text-xs text-slate-600 mt-1'>Lịch trình</Text>
            </View>
          </View>
        )}

        <View className='p-4'>
          <Text className='text-base font-semibold text-slate-900 mb-3'>
            Thông tin cá nhân
          </Text>

          <View className='bg-white rounded-xl border border-slate-200 p-4'>
            <View className='flex-row items-center'>
              <View className='w-10 h-10 rounded-full bg-blue-50 items-center justify-center mr-3'>
                <Mail size={20} color='#0066FF' />
              </View>
              <View className='flex-1'>
                <Text className='text-xs text-slate-600 mb-0.5'>Email</Text>
                <Text className='text-base font-semibold text-slate-900'>
                  {profileData?.email || user?.email}
                </Text>
              </View>
            </View>

            {profileData?.age && (
              <>
                <View className='h-px bg-slate-200 my-4' />
                <View className='flex-row items-center'>
                  <View className='w-10 h-10 rounded-full bg-blue-50 items-center justify-center mr-3'>
                    <Calendar size={20} color='#0066FF' />
                  </View>
                  <View className='flex-1'>
                    <Text className='text-xs text-slate-600 mb-0.5'>Tuổi</Text>
                    <Text className='text-base font-semibold text-slate-900'>
                      {profileData.age}
                    </Text>
                  </View>
                </View>
              </>
            )}
          </View>
        </View>

        <View className='p-4'>
          <Text className='text-base font-semibold text-slate-900 mb-3'>
            Sở thích du lịch
          </Text>

          <View className='bg-white rounded-xl border border-slate-200 p-4'>
            <View className='mb-3'>
              <Text className='text-xs text-slate-600 mb-1'>Năng lượng</Text>
              <Text className='text-base font-semibold text-slate-900'>
                {getEnergyLevelText(profileData?.energy_level || null)}
              </Text>
            </View>

            <View className='h-px bg-slate-200 my-3' />

            <View>
              <Text className='text-xs text-slate-600 mb-1'>Ngân sách</Text>
              <Text className='text-base font-semibold text-slate-900'>
                {formatBudget(
                  profileData?.budget_min || null,
                  profileData?.budget_max || null,
                )}
              </Text>
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
