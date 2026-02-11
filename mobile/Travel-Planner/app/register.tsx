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
import {
  Camera,
  Coffee,
  Mountain,
  Landmark,
  UtensilsCrossed,
  Waves,
  Moon,
  Leaf,
  MapPin,
  Eye,
  EyeOff,
  ArrowLeft,
} from 'lucide-react-native';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { API_ENDPOINTS, setAuthToken } from '@/config/api';
import { useAuth } from '@/contexts/AuthContext';
import { Gender, EnergyLevel, TravelPreference } from '@/types';

const travelPreferences: TravelPreference[] = [
  {
    id: 'photography',
    label: 'Chụp hình',
    icon: 'Camera',
    color: 'bg-yellow-100',
  },
  { id: 'coffee', label: 'Cà phê', icon: 'Coffee', color: 'bg-amber-100' },
  { id: 'drink', label: 'Đồ uống', icon: 'Coffee', color: 'bg-amber-100' },
  {
    id: 'trekking',
    label: 'Trekking',
    icon: 'Mountain',
    color: 'bg-green-100',
  },
  { id: 'museum', label: 'Bảo tàng', icon: 'Landmark', color: 'bg-purple-100' },
  {
    id: 'food',
    label: 'Ẩm thực',
    icon: 'UtensilsCrossed',
    color: 'bg-orange-100',
  },
  { id: 'beach', label: 'Biển', icon: 'Waves', color: 'bg-cyan-100' },
  { id: 'nightlife', label: 'Nightlife', icon: 'Moon', color: 'bg-indigo-100' },
  { id: 'relaxed', label: 'Chill', icon: 'Leaf', color: 'bg-teal-100' },
  { id: 'culture', label: 'Văn hóa', icon: 'MapPin', color: 'bg-pink-100' },
];

const IconMap: any = {
  Camera,
  Coffee,
  Mountain,
  Landmark,
  UtensilsCrossed,
  Waves,
  Moon,
  Leaf,
  MapPin,
};

export default function RegisterScreen() {
  const router = useRouter();
  const { login } = useAuth();
  const [step, setStep] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  // Step 1
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');

  // Step 2
  const [age, setAge] = useState('');
  const [gender, setGender] = useState<Gender>(null);
  const [energyLevel, setEnergyLevel] = useState<EnergyLevel>(null);
  const [budgetMin, setBudgetMin] = useState('5');
  const [budgetMax, setBudgetMax] = useState('10');
  const [selectedPreferences, setSelectedPreferences] = useState<string[]>([]);

  const handleNext = () => {
    if (!email || !password) {
      Alert.alert('Lỗi', 'Vui lòng nhập email và mật khẩu');
      return;
    }
    setStep(2);
  };

  const handleSubmit = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(API_ENDPOINTS.AUTH.REGISTER, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        body: JSON.stringify({
          email,
          password,
          full_name: fullName || null,
          age: age ? parseInt(age) : null,
          gender: gender || null,
          energy_level: energyLevel || null,
          budget_min: budgetMin ? parseFloat(budgetMin) * 1000000 : null,
          budget_max: budgetMax ? parseFloat(budgetMax) * 1000000 : null,
          preferences: selectedPreferences || [],
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        Alert.alert('Lỗi', data.detail || 'Đăng ký thất bại');
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

  const togglePreference = (id: string) => {
    setSelectedPreferences((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id],
    );
  };

  return (
    <KeyboardAvoidingView
      className='flex-1'
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ScrollView
        className='flex-1 bg-slate-50'
        showsVerticalScrollIndicator={false}
      >
        <View className='pt-16 px-6 pb-8 items-center'>
          <TouchableOpacity
            onPress={() => (step === 1 ? router.back() : setStep(1))}
            className='absolute left-6 top-16'
          >
            <ArrowLeft size={24} color='#0F172A' />
          </TouchableOpacity>

          <View className='w-20 h-20 rounded-2xl bg-blue-600 items-center justify-center mb-4'>
            <Text className='text-5xl'>✈️</Text>
          </View>
          <Text className='text-3xl font-bold text-slate-900 mb-2'>
            Đăng ký tài khoản
          </Text>
          <Text className='text-base text-slate-600'>
            {step === 1 ? 'Tạo tài khoản mới' : 'Cá nhân hóa trải nghiệm'}
          </Text>

          {/* Progress Indicator */}
          <View className='flex-row gap-2 mt-4'>
            <View
              className={`h-1.5 w-16 rounded-full ${step === 1 ? 'bg-blue-600' : 'bg-blue-600'}`}
            />
            <View
              className={`h-1.5 w-16 rounded-full ${step === 2 ? 'bg-blue-600' : 'bg-slate-300'}`}
            />
          </View>
        </View>

        {/* Step 1: Basic Info */}
        {step === 1 && (
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

            <Input
              label='Họ tên (tùy chọn)'
              value={fullName}
              onChangeText={setFullName}
              placeholder='Nguyễn Văn A'
            />

            <Button onPress={handleNext}>Tiếp tục</Button>

            <TouchableOpacity
              onPress={() => router.back()}
              className='mt-4 items-center'
            >
              <Text className='text-sm text-blue-600 font-semibold'>
                Đã có tài khoản? Đăng nhập
              </Text>
            </TouchableOpacity>
          </View>
        )}

        {/* Step 2: Preferences */}
        {step === 2 && (
          <View className='px-6 pb-10'>
            <Input
              label='Tuổi (tùy chọn)'
              value={age}
              onChangeText={setAge}
              placeholder='25'
              keyboardType='numeric'
            />

            <Text className='text-sm font-semibold text-slate-900 mb-2 mt-2'>
              Giới tính
            </Text>
            <View className='flex-row gap-2 mb-4'>
              {[
                { value: 'male', label: 'Nam' },
                { value: 'female', label: 'Nữ' },
                { value: 'other', label: 'Khác' },
              ].map((option) => (
                <TouchableOpacity
                  key={option.value}
                  className={`flex-1 py-3 px-4 rounded-xl border items-center ${
                    gender === option.value
                      ? 'bg-blue-600 border-blue-600'
                      : 'bg-white border-slate-200'
                  }`}
                  onPress={() => setGender(option.value as Gender)}
                >
                  <Text
                    className={`text-sm font-semibold ${
                      gender === option.value ? 'text-white' : 'text-slate-600'
                    }`}
                  >
                    {option.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            <Text className='text-sm font-semibold text-slate-900 mb-2 mt-2'>
              Mức năng lượng
            </Text>
            <View className='flex-row gap-2 mb-4'>
              {[
                { value: 'low', label: 'Chill' },
                { value: 'medium', label: 'Trung bình' },
                { value: 'high', label: 'Năng động' },
              ].map((option) => (
                <TouchableOpacity
                  key={option.value}
                  className={`flex-1 py-3 px-4 rounded-xl border items-center ${
                    energyLevel === option.value
                      ? 'bg-blue-600 border-blue-600'
                      : 'bg-white border-slate-200'
                  }`}
                  onPress={() => setEnergyLevel(option.value as EnergyLevel)}
                >
                  <Text
                    className={`text-sm font-semibold ${
                      energyLevel === option.value
                        ? 'text-white'
                        : 'text-slate-600'
                    }`}
                  >
                    {option.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            <Text className='text-sm font-semibold text-slate-900 mb-2 mt-2'>
              Ngân sách (triệu VNĐ)
            </Text>
            <View className='flex-row items-center gap-3 mb-4'>
              <Input
                value={budgetMin}
                onChangeText={setBudgetMin}
                placeholder='5'
                keyboardType='numeric'
                containerClassName='flex-1 mb-0'
              />
              <Text className='text-lg text-slate-600 -mt-4'>-</Text>
              <Input
                value={budgetMax}
                onChangeText={setBudgetMax}
                placeholder='10'
                keyboardType='numeric'
                containerClassName='flex-1 mb-0'
              />
            </View>

            <Text className='text-sm font-semibold text-slate-900 mb-2 mt-2'>
              Sở thích du lịch
            </Text>
            <View className='flex-row flex-wrap gap-2 mb-6'>
              {travelPreferences.map((pref) => {
                const Icon = IconMap[pref.icon];
                return (
                  <TouchableOpacity
                    key={pref.id}
                    className={`flex-row items-center py-2 px-3 rounded-full ${pref.color} ${
                      selectedPreferences.includes(pref.id)
                        ? 'border-2 border-blue-600'
                        : ''
                    }`}
                    onPress={() => togglePreference(pref.id)}
                  >
                    {Icon && <Icon size={16} color='#0F172A' />}
                    <Text className='text-xs text-slate-900 font-semibold ml-1.5'>
                      {pref.label}
                    </Text>
                  </TouchableOpacity>
                );
              })}
            </View>

            <View className='flex-row gap-3'>
              <Button
                variant='outline'
                onPress={() => setStep(1)}
                className='flex-1'
              >
                Quay lại
              </Button>
              <Button
                onPress={handleSubmit}
                loading={isLoading}
                className='flex-1'
              >
                Hoàn tất
              </Button>
            </View>
          </View>
        )}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
