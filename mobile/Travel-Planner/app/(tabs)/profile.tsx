import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  Alert,
  ActivityIndicator,
  TouchableOpacity,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import {
  User as UserIcon,
  Mail,
  Calendar,
  MapPin,
  Heart,
  Bookmark,
  Moon,
  Sun,
  Monitor,
  Edit,
  Zap,
  Camera,
  Coffee,
  Mountain,
  Landmark,
  UtensilsCrossed,
  Waves,
  Leaf,
  X,
  Check,
} from 'lucide-react-native';
import { useAuth } from '@/contexts/AuthContext';
import { useTheme } from '@/contexts/ThemeContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
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

const travelPreferences = [
  { id: 'photography', label: 'Chụp hình', icon: Camera },
  { id: 'coffee', label: 'Cà phê', icon: Coffee },
  { id: 'drink', label: 'Đồ uống', icon: Coffee },
  { id: 'trekking', label: 'Trekking', icon: Mountain },
  { id: 'museum', label: 'Bảo tàng', icon: Landmark },
  { id: 'food', label: 'Ẩm thực', icon: UtensilsCrossed },
  { id: 'beach', label: 'Biển', icon: Waves },
  { id: 'nightlife', label: 'Nightlife', icon: Moon },
  { id: 'relaxed', label: 'Chill', icon: Leaf },
  { id: 'culture', label: 'Văn hóa', icon: MapPin },
];

export default function ProfileScreen() {
  const router = useRouter();
  const { user, logout } = useAuth();
  const { theme, setTheme, activeTheme, colors } = useTheme();
  const [profileData, setProfileData] = useState<ProfileData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // Editable fields
  const [name, setName] = useState('');
  const [age, setAge] = useState('');
  const [gender, setGender] = useState<'male' | 'female' | 'other' | null>(
    null,
  );
  const [energyLevel, setEnergyLevel] = useState<
    'low' | 'medium' | 'high' | null
  >(null);
  const [budgetMin, setBudgetMin] = useState('5');
  const [budgetMax, setBudgetMax] = useState('10');
  const [selectedPreferences, setSelectedPreferences] = useState<string[]>([]);

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
        // Initialize editable fields
        setName(data.full_name || '');
        setAge(data.age ? data.age.toString() : '');
        setGender(data.gender || null);
        setEnergyLevel(data.energy_level || null);
        const convertToMillion = (value: number | null): string => {
          if (!value) return '5';
          return value < 1000000
            ? value.toString()
            : (value / 1000000).toFixed(0);
        };
        setBudgetMin(convertToMillion(data.budget_min));
        setBudgetMax(convertToMillion(data.budget_max));
        setSelectedPreferences(data.preferences || []);
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

  const getGenderText = (g: string | null) => {
    const genders: Record<string, string> = {
      male: 'Nam',
      female: 'Nữ',
      other: 'Khác',
    };
    return g ? genders[g] : 'Chưa thiết lập';
  };

  const togglePreference = (id: string) => {
    setSelectedPreferences((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id],
    );
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(API_ENDPOINTS.PROFILE.UPDATE, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          full_name: name || null,
          age: age ? parseInt(age) : null,
          gender: gender || null,
          energy_level: energyLevel || null,
          budget_min: budgetMin ? parseFloat(budgetMin) * 1000000 : null,
          budget_max: budgetMax ? parseFloat(budgetMax) * 1000000 : null,
          preferences: selectedPreferences || [],
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setProfileData(data);
        setIsEditing(false);
        Alert.alert('Thành công', 'Cập nhật thông tin thành công');
      } else {
        Alert.alert('Lỗi', 'Không thể cập nhật thông tin');
      }
    } catch (error) {
      console.error('Error updating profile:', error);
      Alert.alert('Lỗi', 'Có lỗi xảy ra khi cập nhật thông tin');
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    // Reset to original values
    if (profileData) {
      setName(profileData.full_name || '');
      setAge(profileData.age ? profileData.age.toString() : '');
      setGender(profileData.gender || null);
      setEnergyLevel(profileData.energy_level || null);
      const convertToMillion = (value: number | null): string => {
        if (!value) return '5';
        return value < 1000000
          ? value.toString()
          : (value / 1000000).toFixed(0);
      };
      setBudgetMin(convertToMillion(profileData.budget_min));
      setBudgetMax(convertToMillion(profileData.budget_max));
      setSelectedPreferences(profileData.preferences || []);
    }
    setIsEditing(false);
  };

  if (isLoading) {
    return (
      <SafeAreaView
        className='flex-1'
        edges={['top']}
        style={{ backgroundColor: colors.background }}
      >
        <View className='flex-1 items-center justify-center'>
          <ActivityIndicator size='large' color={colors.primary} />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView
      className='flex-1'
      edges={['top']}
      style={{ backgroundColor: colors.background }}
    >
      <View
        className='px-4 py-4 border-b'
        style={{ backgroundColor: colors.card, borderColor: colors.border }}
      >
        <Text
          className='text-2xl font-bold'
          style={{ color: colors.foreground }}
        >
          Hồ sơ cá nhân
        </Text>
      </View>

      <ScrollView className='flex-1'>
        <View
          className='items-center py-6 mt-4 mx-4 rounded-2xl border'
          style={{ backgroundColor: colors.card, borderColor: colors.border }}
        >
          <View
            className='w-20 h-20 rounded-full items-center justify-center mb-4'
            style={{ backgroundColor: colors.primary }}
          >
            <UserIcon size={40} color='#FFFFFF' />
          </View>

          {isEditing ? (
            <View className='w-full px-4'>
              <Input
                label='Họ tên'
                value={name}
                onChangeText={setName}
                placeholder='Nguyễn Văn A'
                containerClassName='mb-2'
              />
            </View>
          ) : (
            <>
              <Text
                className='text-xl font-bold mb-1'
                style={{ color: colors.foreground }}
              >
                {profileData?.full_name || user?.full_name || 'Người dùng'}
              </Text>
              <Text
                className='text-sm'
                style={{ color: colors.mutedForeground }}
              >
                {profileData?.email || user?.email}
              </Text>
            </>
          )}

          <TouchableOpacity
            onPress={() => (isEditing ? handleSave() : setIsEditing(true))}
            className='mt-4 px-6 py-2.5 rounded-xl flex-row items-center'
            style={{
              backgroundColor: isEditing ? colors.primary : colors.accent,
            }}
            disabled={isSaving}
          >
            {isSaving ? (
              <ActivityIndicator size='small' color='#FFFFFF' />
            ) : (
              <>
                {isEditing ? (
                  <Check size={16} color='#FFFFFF' />
                ) : (
                  <Edit size={16} color={colors.primary} />
                )}
                <Text
                  className='text-sm font-semibold ml-2'
                  style={{ color: isEditing ? '#FFFFFF' : colors.primary }}
                >
                  {isEditing ? 'Lưu thay đổi' : 'Chỉnh sửa'}
                </Text>
              </>
            )}
          </TouchableOpacity>

          {isEditing && (
            <TouchableOpacity
              onPress={handleCancel}
              className='mt-2 px-6 py-2.5 rounded-xl'
              disabled={isSaving}
            >
              <Text
                className='text-sm font-semibold'
                style={{ color: colors.mutedForeground }}
              >
                Hủy
              </Text>
            </TouchableOpacity>
          )}
        </View>

        {profileData?.stats && (
          <View className='flex-row px-4 mt-4 gap-3'>
            <View
              className='flex-1 rounded-xl border p-4 items-center'
              style={{
                backgroundColor: colors.card,
                borderColor: colors.border,
              }}
            >
              <MapPin size={24} color={colors.primary} />
              <Text
                className='text-2xl font-bold mt-2'
                style={{ color: colors.foreground }}
              >
                {profileData.stats.trips_planned}
              </Text>
              <Text
                className='text-xs mt-1'
                style={{ color: colors.mutedForeground }}
              >
                Chuyến đi
              </Text>
            </View>
            <View
              className='flex-1 rounded-xl border p-4 items-center'
              style={{
                backgroundColor: colors.card,
                borderColor: colors.border,
              }}
            >
              <Heart size={24} color={colors.primary} />
              <Text
                className='text-2xl font-bold mt-2'
                style={{ color: colors.foreground }}
              >
                {profileData.stats.places_visited}
              </Text>
              <Text
                className='text-xs mt-1'
                style={{ color: colors.mutedForeground }}
              >
                Địa điểm
              </Text>
            </View>
            <View
              className='flex-1 rounded-xl border p-4 items-center'
              style={{
                backgroundColor: colors.card,
                borderColor: colors.border,
              }}
            >
              <Bookmark size={24} color={colors.primary} />
              <Text
                className='text-2xl font-bold mt-2'
                style={{ color: colors.foreground }}
              >
                {profileData.stats.saved_itineraries}
              </Text>
              <Text
                className='text-xs mt-1'
                style={{ color: colors.mutedForeground }}
              >
                Lịch trình
              </Text>
            </View>
          </View>
        )}

        <View className='p-4'>
          <Text
            className='text-base font-semibold mb-3'
            style={{ color: colors.foreground }}
          >
            Thông tin cá nhân
          </Text>

          <View
            className='rounded-xl border p-4'
            style={{ backgroundColor: colors.card, borderColor: colors.border }}
          >
            {/* Email */}
            <View className='flex-row items-center'>
              <View
                className='w-10 h-10 rounded-full items-center justify-center mr-3'
                style={{ backgroundColor: colors.accent }}
              >
                <Mail size={20} color={colors.primary} />
              </View>
              <View className='flex-1'>
                <Text
                  className='text-xs mb-0.5'
                  style={{ color: colors.mutedForeground }}
                >
                  Email
                </Text>
                <Text
                  className='text-base font-semibold'
                  style={{ color: colors.foreground }}
                >
                  {profileData?.email || user?.email}
                </Text>
              </View>
            </View>

            {/* Age */}
            <View
              className='h-px my-4'
              style={{ backgroundColor: colors.border }}
            />
            <View className='flex-row items-center'>
              <View
                className='w-10 h-10 rounded-full items-center justify-center mr-3'
                style={{ backgroundColor: colors.accent }}
              >
                <Calendar size={20} color={colors.primary} />
              </View>
              <View className='flex-1'>
                <Text
                  className='text-xs mb-0.5'
                  style={{ color: colors.mutedForeground }}
                >
                  Tuổi
                </Text>
                {isEditing ? (
                  <Input
                    value={age}
                    onChangeText={setAge}
                    placeholder='25'
                    keyboardType='numeric'
                    containerClassName='mb-0 mt-1'
                  />
                ) : (
                  <Text
                    className='text-base font-semibold'
                    style={{ color: colors.foreground }}
                  >
                    {age || 'Chưa thiết lập'}
                  </Text>
                )}
              </View>
            </View>

            {/* Gender */}
            <View
              className='h-px my-4'
              style={{ backgroundColor: colors.border }}
            />
            <View>
              <Text
                className='text-xs mb-2'
                style={{ color: colors.mutedForeground }}
              >
                Giới tính
              </Text>
              {isEditing ? (
                <View className='flex-row gap-2'>
                  {[
                    { value: 'male' as const, label: 'Nam' },
                    { value: 'female' as const, label: 'Nữ' },
                    { value: 'other' as const, label: 'Khác' },
                  ].map((option) => (
                    <TouchableOpacity
                      key={option.value}
                      className='flex-1 py-2 px-3 rounded-lg border items-center'
                      style={{
                        backgroundColor:
                          gender === option.value
                            ? colors.primary
                            : colors.card,
                        borderColor:
                          gender === option.value
                            ? colors.primary
                            : colors.border,
                      }}
                      onPress={() => setGender(option.value)}
                    >
                      <Text
                        className='text-sm font-semibold'
                        style={{
                          color:
                            gender === option.value
                              ? '#FFFFFF'
                              : colors.foreground,
                        }}
                      >
                        {option.label}
                      </Text>
                    </TouchableOpacity>
                  ))}
                </View>
              ) : (
                <Text
                  className='text-base font-semibold'
                  style={{ color: colors.foreground }}
                >
                  {getGenderText(gender)}
                </Text>
              )}
            </View>
          </View>
        </View>

        <View className='p-4'>
          <Text
            className='text-base font-semibold mb-3'
            style={{ color: colors.foreground }}
          >
            Sở thích du lịch
          </Text>

          <View
            className='rounded-xl border p-4'
            style={{ backgroundColor: colors.card, borderColor: colors.border }}
          >
            {/* Energy Level */}
            <View className='mb-3'>
              <Text
                className='text-xs mb-2'
                style={{ color: colors.mutedForeground }}
              >
                Mức năng lượng
              </Text>
              {isEditing ? (
                <View className='flex-row gap-2'>
                  {[
                    { value: 'low' as const, label: 'Chill' },
                    { value: 'medium' as const, label: 'Trung bình' },
                    { value: 'high' as const, label: 'Năng động' },
                  ].map((option) => (
                    <TouchableOpacity
                      key={option.value}
                      className='flex-1 py-2 px-3 rounded-lg border items-center'
                      style={{
                        backgroundColor:
                          energyLevel === option.value
                            ? colors.primary
                            : colors.card,
                        borderColor:
                          energyLevel === option.value
                            ? colors.primary
                            : colors.border,
                      }}
                      onPress={() => setEnergyLevel(option.value)}
                    >
                      <Text
                        className='text-sm font-semibold'
                        style={{
                          color:
                            energyLevel === option.value
                              ? '#FFFFFF'
                              : colors.foreground,
                        }}
                      >
                        {option.label}
                      </Text>
                    </TouchableOpacity>
                  ))}
                </View>
              ) : (
                <Text
                  className='text-base font-semibold'
                  style={{ color: colors.foreground }}
                >
                  {getEnergyLevelText(energyLevel)}
                </Text>
              )}
            </View>

            <View
              className='h-px my-3'
              style={{ backgroundColor: colors.border }}
            />

            {/* Budget */}
            <View>
              <Text
                className='text-xs mb-2'
                style={{ color: colors.mutedForeground }}
              >
                Ngân sách (triệu VNĐ)
              </Text>
              {isEditing ? (
                <View className='flex-row items-center gap-3'>
                  <Input
                    value={budgetMin}
                    onChangeText={setBudgetMin}
                    placeholder='5'
                    keyboardType='numeric'
                    containerClassName='flex-1 mb-0'
                  />
                  <Text
                    className='-mt-4'
                    style={{ color: colors.mutedForeground }}
                  >
                    -
                  </Text>
                  <Input
                    value={budgetMax}
                    onChangeText={setBudgetMax}
                    placeholder='10'
                    keyboardType='numeric'
                    containerClassName='flex-1 mb-0'
                  />
                </View>
              ) : (
                <Text
                  className='text-base font-semibold'
                  style={{ color: colors.foreground }}
                >
                  {formatBudget(
                    profileData?.budget_min || null,
                    profileData?.budget_max || null,
                  )}
                </Text>
              )}
            </View>

            {/* Travel Preferences */}
            <View
              className='h-px my-3'
              style={{ backgroundColor: colors.border }}
            />
            <View>
              <Text
                className='text-xs mb-2'
                style={{ color: colors.mutedForeground }}
              >
                Sở thích
              </Text>
              <View className='flex-row flex-wrap gap-2'>
                {travelPreferences.map((pref) => {
                  const Icon = pref.icon;
                  const isSelected = selectedPreferences.includes(pref.id);
                  return (
                    <TouchableOpacity
                      key={pref.id}
                      className='flex-row items-center py-2 px-3 rounded-full border'
                      style={{
                        backgroundColor: isSelected
                          ? colors.accent
                          : colors.card,
                        borderColor: isSelected
                          ? colors.primary
                          : colors.border,
                        borderWidth: isSelected ? 2 : 1,
                      }}
                      onPress={() => isEditing && togglePreference(pref.id)}
                      disabled={!isEditing}
                    >
                      <Icon
                        size={14}
                        color={
                          isSelected ? colors.primary : colors.mutedForeground
                        }
                      />
                      <Text
                        className='text-xs font-semibold ml-1.5'
                        style={{
                          color: isSelected
                            ? colors.foreground
                            : colors.mutedForeground,
                        }}
                      >
                        {pref.label}
                      </Text>
                    </TouchableOpacity>
                  );
                })}
              </View>
            </View>
          </View>
        </View>

        <View className='p-4'>
          <Text
            className='text-base font-semibold mb-3'
            style={{ color: colors.foreground }}
          >
            Giao diện
          </Text>

          <View
            className='rounded-xl border p-3'
            style={{ backgroundColor: colors.card, borderColor: colors.border }}
          >
            <TouchableOpacity
              onPress={() => setTheme('light')}
              className='flex-row items-center p-3 rounded-lg'
              style={{
                backgroundColor:
                  theme === 'light' ? colors.accent : 'transparent',
              }}
              activeOpacity={0.7}
            >
              <View
                className='w-10 h-10 rounded-full items-center justify-center mr-3'
                style={{ backgroundColor: colors.accent }}
              >
                <Sun
                  size={20}
                  color={
                    theme === 'light' ? colors.primary : colors.mutedForeground
                  }
                />
              </View>
              <View className='flex-1'>
                <Text
                  className='text-base font-semibold'
                  style={{ color: colors.foreground }}
                >
                  Sáng
                </Text>
              </View>
              {theme === 'light' && (
                <View
                  className='w-5 h-5 rounded-full items-center justify-center'
                  style={{ backgroundColor: colors.primary }}
                >
                  <View className='w-2 h-2 rounded-full bg-white' />
                </View>
              )}
            </TouchableOpacity>

            <TouchableOpacity
              onPress={() => setTheme('dark')}
              className='flex-row items-center p-3 rounded-lg mt-2'
              style={{
                backgroundColor:
                  theme === 'dark' ? colors.accent : 'transparent',
              }}
              activeOpacity={0.7}
            >
              <View
                className='w-10 h-10 rounded-full items-center justify-center mr-3'
                style={{ backgroundColor: colors.accent }}
              >
                <Moon
                  size={20}
                  color={
                    theme === 'dark' ? colors.primary : colors.mutedForeground
                  }
                />
              </View>
              <View className='flex-1'>
                <Text
                  className='text-base font-semibold'
                  style={{ color: colors.foreground }}
                >
                  Tối
                </Text>
              </View>
              {theme === 'dark' && (
                <View
                  className='w-5 h-5 rounded-full items-center justify-center'
                  style={{ backgroundColor: colors.primary }}
                >
                  <View className='w-2 h-2 rounded-full bg-white' />
                </View>
              )}
            </TouchableOpacity>

            <TouchableOpacity
              onPress={() => setTheme('system')}
              className='flex-row items-center p-3 rounded-lg mt-2'
              style={{
                backgroundColor:
                  theme === 'system' ? colors.accent : 'transparent',
              }}
              activeOpacity={0.7}
            >
              <View
                className='w-10 h-10 rounded-full items-center justify-center mr-3'
                style={{ backgroundColor: colors.accent }}
              >
                <Monitor
                  size={20}
                  color={
                    theme === 'system' ? colors.primary : colors.mutedForeground
                  }
                />
              </View>
              <View className='flex-1'>
                <Text
                  className='text-base font-semibold'
                  style={{ color: colors.foreground }}
                >
                  Theo hệ thống
                </Text>
              </View>
              {theme === 'system' && (
                <View
                  className='w-5 h-5 rounded-full items-center justify-center'
                  style={{ backgroundColor: colors.primary }}
                >
                  <View className='w-2 h-2 rounded-full bg-white' />
                </View>
              )}
            </TouchableOpacity>
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
