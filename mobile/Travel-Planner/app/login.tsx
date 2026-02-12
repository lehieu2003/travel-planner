import React, { useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  KeyboardAvoidingView,
  Platform,
  Alert,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Eye, EyeOff } from 'lucide-react-native';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { API_ENDPOINTS, setAuthToken } from '@/config/api';
import { useAuth } from '@/contexts/AuthContext';
import { useTheme } from '@/contexts/ThemeContext';

export default function LoginScreen() {
  const { colors } = useTheme();
  const router = useRouter();
  const { login } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = async () => {
    if (!email || !password) {
      Alert.alert('Lỗi', 'Vui lòng nhập email và mật khẩu');
      return;
    }

    setIsLoading(true);
    try {
      const loginData = {
        email: email,
        password: password,
      };

      const response = await fetch(API_ENDPOINTS.AUTH.LOGIN, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        body: JSON.stringify(loginData),
      });

      const data = await response.json();

      if (!response.ok) {
        Alert.alert('Lỗi', 'Email hoặc mật khẩu không đúng');
        return;
      }

      await setAuthToken(data.access_token);
      await login(data.access_token);
      router.replace('/(tabs)');
    } catch {
      Alert.alert('Lỗi', 'Không thể kết nối đến server');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      className='flex-1'
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      style={{ backgroundColor: colors.background }}
    >
      <ScrollView
        className='flex-1'
        showsVerticalScrollIndicator={false}
        style={{ backgroundColor: colors.background }}
      >
        <View className='pt-16 px-6 pb-8 items-center'>
          <View
            className='w-20 h-20 rounded-2xl items-center justify-center mb-4'
            style={{ backgroundColor: colors.primary }}
          >
            <Text className='text-5xl'>✈️</Text>
          </View>
          <Text
            className='text-3xl font-bold mb-2'
            style={{ color: colors.foreground }}
          >
            Travel Planner
          </Text>
          <Text className='text-base' style={{ color: colors.mutedForeground }}>
            Chào mừng trở lại
          </Text>
        </View>

        <View className='px-6 pb-10'>
          <Input
            label='Email'
            value={email}
            onChangeText={setEmail}
            placeholder='email@example.com'
            keyboardType='email-address'
            autoCapitalize='none'
          />

          <View className='relative'>
            <Input
              label='Mật khẩu'
              value={password}
              onChangeText={setPassword}
              placeholder='••••••••'
              secureTextEntry={!showPassword}
            />
            <TouchableOpacity
              className='absolute right-4 top-11'
              onPress={() => setShowPassword(!showPassword)}
            >
              {showPassword ? (
                <EyeOff size={20} color='#94A3B8' />
              ) : (
                <Eye size={20} color='#94A3B8' />
              )}
            </TouchableOpacity>
          </View>

          <Button onPress={handleSubmit} loading={isLoading}>
            Đăng nhập
          </Button>

          <TouchableOpacity
            onPress={() => router.push('/register' as any)}
            className='mt-4 items-center'
          >
            <Text
              className='text-sm font-semibold'
              style={{ color: colors.primary }}
            >
              Chưa có tài khoản? Đăng ký
            </Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
