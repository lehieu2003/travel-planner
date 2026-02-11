import { useState, useEffect } from 'react';
import {
  Edit,
  Mail,
  User,
  Coffee,
  Waves,
  Calendar,
  Camera,
  Mountain,
  Landmark,
  UtensilsCrossed,
  Moon,
  Leaf,
  MapPin,
  X,
  Check,
  Activity,
  Zap,
  DollarSign,
  Sun,
} from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from './ui/avatar';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Slider } from './ui/slider';
import { API_ENDPOINTS, getAuthHeaders } from '../config/api';

type Gender = 'male' | 'female' | 'other';
type EnergyLevel = 'low' | 'medium' | 'high';

interface TravelPreference {
  id: string;
  label: string;
  icon: any;
  color: string;
}

const travelPreferences: TravelPreference[] = [
  {
    id: 'photography',
    label: 'Chụp hình',
    icon: Camera,
    color: 'bg-yellow-100 text-yellow-700 border-yellow-200',
  },
  {
    id: 'coffee',
    label: 'Cà phê',
    icon: Coffee,
    color: 'bg-amber-100 text-amber-700 border-amber-200',
  },
  {
    id: 'drink',
    label: 'Đồ uống',
    icon: Coffee,
    color: 'bg-amber-100 text-amber-700 border-amber-200',
  },
  {
    id: 'trekking',
    label: 'Trekking',
    icon: Mountain,
    color: 'bg-green-100 text-green-700 border-green-200',
  },
  {
    id: 'museum',
    label: 'Bảo tàng / Nghệ thuật',
    icon: Landmark,
    color: 'bg-purple-100 text-purple-700 border-purple-200',
  },
  {
    id: 'food',
    label: 'Ẩm thực địa phương',
    icon: UtensilsCrossed,
    color: 'bg-orange-100 text-orange-700 border-orange-200',
  },
  {
    id: 'beach',
    label: 'Biển / nghỉ dưỡng',
    icon: Waves,
    color: 'bg-cyan-100 text-cyan-700 border-cyan-200',
  },
  {
    id: 'nightlife',
    label: 'Nightlife',
    icon: Moon,
    color: 'bg-indigo-100 text-indigo-700 border-indigo-200',
  },
  {
    id: 'relaxed',
    label: 'Chill style',
    icon: Leaf,
    color: 'bg-teal-100 text-teal-700 border-teal-200',
  },
  {
    id: 'culture',
    label: 'Khám phá văn hóa',
    icon: MapPin,
    color: 'bg-pink-100 text-pink-700 border-pink-200',
  },
];

interface ProfileData {
  id: number;
  email: string;
  full_name: string | null;
  age: number | null;
  gender: Gender | null;
  energy_level: EnergyLevel | null;
  budget_min: number | null;
  budget_max: number | null;
  preferences: string[];
  stats: {
    tripsPlanned: number;
    placesVisited: number;
    savedItineraries: number;
  };
}

interface ConversationItem {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

const GENDER_LABELS = {
  male: 'Nam',
  female: 'Nữ',
  other: 'Khác',
};

const ENERGY_LABELS = {
  low: 'Thấp',
  medium: 'Vừa',
  high: 'Cao',
};

export function Profile() {
  const { theme, toggleTheme } = useTheme();
  const [isEditing, setIsEditing] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [profileData, setProfileData] = useState<ProfileData | null>(null);
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [isLoadingConversations, setIsLoadingConversations] = useState(false);

  const [name, setName] = useState('');
  const [age, setAge] = useState('');
  const [gender, setGender] = useState<Gender | null>(null);
  const [energyLevel, setEnergyLevel] = useState<EnergyLevel | null>(null);
  const [budgetRange, setBudgetRange] = useState<[number, number]>([5, 10]);
  const [selectedPreferences, setSelectedPreferences] = useState<string[]>([]);

  const fetchConversations = async () => {
    setIsLoadingConversations(true);
    try {
      const response = await fetch(API_ENDPOINTS.CONVERSATIONS.LIST, {
        headers: getAuthHeaders(),
      });

      if (!response.ok) {
        console.error('Failed to load conversations');
        return;
      }

      const data = await response.json();
      // Sort by updated_at descending and take top 3
      const sortedConversations = data
        .sort(
          (a: ConversationItem, b: ConversationItem) =>
            new Date(b.updated_at || b.created_at).getTime() -
            new Date(a.updated_at || a.created_at).getTime(),
        )
        .slice(0, 3);
      setConversations(sortedConversations);
    } catch (error) {
      console.error('Error loading conversations:', error);
    } finally {
      setIsLoadingConversations(false);
    }
  };

  const fetchProfile = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(API_ENDPOINTS.PROFILE.GET, {
        headers: getAuthHeaders(),
      });

      if (!response.ok) {
        throw new Error('Không thể tải thông tin hồ sơ');
      }

      const data = await response.json();
      setProfileData(data);
      setName(data.full_name || '');
      setAge(data.age ? data.age.toString() : '');
      setGender(data.gender || null);
      setEnergyLevel(data.energy_level || null);
      // Convert from VND to million VND for display
      // Handle both old format (already in millions) and new format (in VND)
      // If value < 1000000, assume it's already in millions, otherwise convert from VND
      const convertToMillion = (value: number | null | undefined): number => {
        if (value === null || value === undefined) return 5;
        if (value < 1000000) {
          // Already in millions (old format)
          return Math.max(1, value);
        }
        // In VND, convert to millions
        return Math.max(1, Math.round(value / 1000000));
      };
      const budgetMin = convertToMillion(data.budget_min);
      const budgetMax = convertToMillion(data.budget_max);
      setBudgetRange([budgetMin, budgetMax] as [number, number]);
      setSelectedPreferences(data.preferences || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Có lỗi xảy ra');
    } finally {
      setIsLoading(false);
    }
  };

  // Helper function to format relative time
  const getRelativeTime = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffMinutes = Math.floor(diffMs / (1000 * 60));

    if (diffMinutes < 60) {
      return diffMinutes <= 1 ? 'Vừa xong' : `${diffMinutes} phút trước`;
    } else if (diffHours < 24) {
      return `${diffHours} giờ trước`;
    } else if (diffDays === 1) {
      return 'Hôm qua';
    } else if (diffDays < 7) {
      return `${diffDays} ngày trước`;
    } else if (diffDays < 30) {
      const weeks = Math.floor(diffDays / 7);
      return `${weeks} tuần trước`;
    } else {
      const months = Math.floor(diffDays / 30);
      return `${months} tháng trước`;
    }
  };

  // Fetch profile data and conversations on mount
  useEffect(() => {
    fetchProfile();
    fetchConversations();
  }, []);

  // Listen for itinerary saved event to refresh stats
  useEffect(() => {
    const handleItinerarySaved = () => {
      // Only refresh if not currently editing
      if (!isEditing) {
        fetchProfile();
      }
    };

    window.addEventListener('itinerarySaved', handleItinerarySaved);
    return () => {
      window.removeEventListener('itinerarySaved', handleItinerarySaved);
    };
  }, [isEditing]);

  const togglePreference = (id: string) => {
    setSelectedPreferences((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id],
    );
  };

  const handleSave = async () => {
    setIsSaving(true);
    setError(null);
    try {
      const response = await fetch(API_ENDPOINTS.PROFILE.UPDATE, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          full_name: name || null,
          age: age ? parseInt(age) : null,
          gender: gender || null,
          energy_level: energyLevel || null,
          // Convert from million VND to VND for backend
          budget_min: budgetRange[0] ? budgetRange[0] * 1000000 : null,
          budget_max: budgetRange[1] ? budgetRange[1] * 1000000 : null,
          preferences: selectedPreferences || [],
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Không thể cập nhật hồ sơ');
      }

      const data = await response.json();
      setProfileData(data);
      setIsEditing(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Có lỗi xảy ra');
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    // Reset to original values from profileData
    if (profileData) {
      setName(profileData.full_name || '');
      setAge(profileData.age ? profileData.age.toString() : '');
      setGender(profileData.gender || null);
      setEnergyLevel(profileData.energy_level || null);
      // Convert from VND to million VND for display
      // Handle both old format (already in millions) and new format (in VND)
      // If value < 1000000, assume it's already in millions, otherwise convert from VND
      const convertToMillion = (value: number | null | undefined): number => {
        if (value === null || value === undefined) return 5;
        if (value < 1000000) {
          // Already in millions (old format)
          return Math.max(1, value);
        }
        // In VND, convert to millions
        return Math.max(1, Math.round(value / 1000000));
      };
      const budgetMin = convertToMillion(profileData.budget_min);
      const budgetMax = convertToMillion(profileData.budget_max);
      setBudgetRange([budgetMin, budgetMax] as [number, number]);
      setSelectedPreferences(profileData.preferences || []);
    }
    setIsEditing(false);
  };

  const selectedPrefsData = travelPreferences.filter((p) =>
    selectedPreferences.includes(p.id),
  );

  if (isLoading) {
    return (
      <div className='p-4 sm:p-6 lg:p-8 bg-[#F8FAFC] dark:bg-[#0f172a] min-h-screen flex items-center justify-center'>
        <div className='text-center'>
          <div className='animate-spin rounded-full h-12 w-12 border-b-2 border-[#0066FF] mx-auto mb-4'></div>
          <p className='text-muted-foreground'>Đang tải thông tin hồ sơ...</p>
        </div>
      </div>
    );
  }

  if (error && !profileData) {
    return (
      <div className='p-4 sm:p-6 lg:p-8 bg-[#F8FAFC] dark:bg-[#0f172a] min-h-screen flex items-center justify-center'>
        <div className='text-center'>
          <p className='text-red-600 dark:text-red-400 mb-4'>{error}</p>
          <Button onClick={() => window.location.reload()}>Thử lại</Button>
        </div>
      </div>
    );
  }

  const email = profileData?.email || '';
  const avatar = `https://api.dicebear.com/7.x/avataaars/svg?seed=${email}`;
  const stats = profileData?.stats || {
    tripsPlanned: 0,
    placesVisited: 0,
    savedItineraries: 0,
  };

  return (
    <div className='p-4 sm:p-6 lg:p-8 bg-[#F8FAFC] dark:bg-[#0f172a] min-h-screen'>
      <div className='max-w-4xl mx-auto space-y-6'>
        {/* Header */}
        <div>
          <h2 className='mb-2 dark:text-foreground'>
            Hồ sơ cá nhân & Sở thích du lịch
          </h2>
          <p className='text-muted-foreground'>
            Quản lý thông tin cá nhân và sở thích du lịch
          </p>
        </div>

        {error && (
          <div className='p-3 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 text-sm'>
            {error}
          </div>
        )}

        {/* User Info Card */}
        <div className='bg-white dark:bg-card rounded-2xl shadow-sm p-6'>
          <div className='flex flex-col sm:flex-row items-start sm:items-center gap-6 mb-6'>
            <Avatar className='w-24 h-24'>
              <AvatarImage src={avatar} />
              <AvatarFallback className='bg-gradient-to-br from-[#0066FF] to-[#00C29A] text-white'>
                <User className='w-12 h-12' />
              </AvatarFallback>
            </Avatar>

            <div className='flex-1'>
              {!isEditing ? (
                <>
                  <h3 className='mb-1'>{name}</h3>
                  <div className='flex items-center gap-2 text-muted-foreground mb-4'>
                    <Mail className='w-4 h-4' />
                    <span>{email}</span>
                  </div>
                </>
              ) : (
                <div className='space-y-3 mb-4'>
                  <div>
                    <Label htmlFor='name'>Tên</Label>
                    <Input
                      id='name'
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      className='mt-1.5 h-11 rounded-xl'
                    />
                  </div>
                  <div className='flex items-center gap-2 text-muted-foreground'>
                    <Mail className='w-4 h-4' />
                    <span>{email}</span>
                  </div>
                </div>
              )}

              {!isEditing ? (
                <Button
                  variant='outline'
                  className='rounded-xl'
                  onClick={() => setIsEditing(true)}
                >
                  <Edit className='w-4 h-4 mr-2' />
                  Chỉnh sửa thông tin
                </Button>
              ) : (
                <div className='flex gap-2'>
                  <Button
                    className='rounded-xl bg-[#0066FF] hover:bg-[#0052CC]'
                    onClick={handleSave}
                    disabled={isSaving}
                  >
                    <Check className='w-4 h-4 mr-2' />
                    {isSaving ? 'Đang lưu...' : 'Lưu'}
                  </Button>
                  <Button
                    variant='outline'
                    className='rounded-xl'
                    onClick={handleCancel}
                    disabled={isSaving}
                  >
                    <X className='w-4 h-4 mr-2' />
                    Hủy
                  </Button>
                </div>
              )}
            </div>
          </div>

          {/* Stats */}
          <div className='grid grid-cols-3 gap-4 pt-6 border-t border-border'>
            <div className='text-center'>
              <div className='text-[#0066FF] mb-1'>{stats.tripsPlanned}</div>
              <div className='text-muted-foreground'>Chuyến đi</div>
            </div>
            <div className='text-center'>
              <div className='text-[#00C29A] mb-1'>{stats.placesVisited}</div>
              <div className='text-muted-foreground'>Địa điểm</div>
            </div>
            <div className='text-center'>
              <div className='text-[#0066FF] mb-1'>
                {stats.savedItineraries}
              </div>
              <div className='text-muted-foreground'>Đã lưu</div>
            </div>
          </div>
        </div>

        {/* Personal Info Card */}
        <div className='bg-white dark:bg-card rounded-2xl shadow-sm p-6'>
          <h3 className='mb-4 dark:text-foreground'>Thông tin cá nhân</h3>

          <div className='grid sm:grid-cols-2 gap-6'>
            {/* Age */}
            <div>
              <Label className='mb-2 flex items-center gap-2'>
                <User className='w-4 h-4 text-[#0066FF]' />
                Tuổi
              </Label>
              {!isEditing ? (
                <div className='h-11 px-4 rounded-xl bg-gray-50 dark:bg-muted flex items-center'>
                  {age ? `${age} tuổi` : '-'}
                </div>
              ) : (
                <Input
                  type='number'
                  value={age}
                  onChange={(e) => setAge(e.target.value)}
                  className='h-11 rounded-xl'
                  min='1'
                  max='120'
                />
              )}
            </div>

            {/* Gender */}
            <div>
              <Label className='mb-2 flex items-center gap-2'>
                <User className='w-4 h-4 text-[#0066FF]' />
                Giới tính
              </Label>
              {!isEditing ? (
                <div className='h-11 px-4 rounded-xl bg-gray-50 dark:bg-muted flex items-center'>
                  {gender ? GENDER_LABELS[gender] : '-'}
                </div>
              ) : (
                <div className='grid grid-cols-3 gap-2'>
                  <button
                    type='button'
                    onClick={() => setGender('male')}
                    className={`h-11 rounded-xl border-2 transition-all ${
                      gender === 'male'
                        ? 'border-[#0066FF] bg-[#0066FF]/5 text-[#0066FF]'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    Nam
                  </button>
                  <button
                    type='button'
                    onClick={() => setGender('female')}
                    className={`h-11 rounded-xl border-2 transition-all ${
                      gender === 'female'
                        ? 'border-[#0066FF] bg-[#0066FF]/5 text-[#0066FF]'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    Nữ
                  </button>
                  <button
                    type='button'
                    onClick={() => setGender('other')}
                    className={`h-11 rounded-xl border-2 transition-all ${
                      gender === 'other'
                        ? 'border-[#0066FF] bg-[#0066FF]/5 text-[#0066FF]'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    Khác
                  </button>
                </div>
              )}
            </div>

            {/* Energy Level */}
            <div className='sm:col-span-2'>
              <Label className='mb-2 flex items-center gap-2'>
                <Zap className='w-4 h-4 text-[#0066FF]' />
                Mức năng lượng
              </Label>
              {!isEditing ? (
                <div className='h-11 px-4 rounded-xl bg-gray-50 dark:bg-muted flex items-center'>
                  {energyLevel ? ENERGY_LABELS[energyLevel] : '-'}
                </div>
              ) : (
                <div className='grid grid-cols-3 gap-3'>
                  <button
                    type='button'
                    onClick={() => setEnergyLevel('low')}
                    className={`h-11 rounded-xl border-2 transition-all ${
                      energyLevel === 'low'
                        ? 'border-[#0066FF] bg-[#0066FF]/5 text-[#0066FF]'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    Thấp
                  </button>
                  <button
                    type='button'
                    onClick={() => setEnergyLevel('medium')}
                    className={`h-11 rounded-xl border-2 transition-all ${
                      energyLevel === 'medium'
                        ? 'border-[#0066FF] bg-[#0066FF]/5 text-[#0066FF]'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    Vừa
                  </button>
                  <button
                    type='button'
                    onClick={() => setEnergyLevel('high')}
                    className={`h-11 rounded-xl border-2 transition-all ${
                      energyLevel === 'high'
                        ? 'border-[#0066FF] bg-[#0066FF]/5 text-[#0066FF]'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    Cao
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Budget Range Card */}
        <div className='bg-white dark:bg-card rounded-2xl shadow-sm p-6'>
          <Label className='mb-4 flex items-center gap-2'>
            <DollarSign className='w-4 h-4 text-[#0066FF]' />
            Phạm vi ngân sách
          </Label>

          <div className='bg-gray-50 dark:bg-muted rounded-xl p-4 mb-3'>
            <div className='text-center mb-4'>
              <span className='text-[#0066FF]'>
                {budgetRange[0]} - {budgetRange[1]} triệu VND
              </span>
            </div>
            <Slider
              value={budgetRange}
              onValueChange={(value) =>
                setBudgetRange(value as [number, number])
              }
              min={1}
              max={20}
              step={1}
              className='w-full'
              disabled={!isEditing}
            />
          </div>
          <div className='flex justify-between text-sm text-muted-foreground'>
            <span>1M</span>
            <span>20M</span>
          </div>
          <p className='text-sm text-muted-foreground mt-2'>
            Ngân sách tham khảo, có thể thay đổi khi lập lịch trình
          </p>
        </div>

        {/* Travel Preferences Card */}
        <div className='bg-white dark:bg-card rounded-2xl shadow-sm p-6'>
          <div className='flex items-center justify-between mb-6'>
            <div>
              <h3 className='mb-1 dark:text-foreground'>Sở thích du lịch</h3>
              <p className='text-muted-foreground'>
                {isEditing
                  ? 'Chọn những gì bạn yêu thích'
                  : 'Sở thích đã lưu của bạn'}
              </p>
            </div>
          </div>

          {/* Preference Chips */}
          <div className='flex flex-wrap gap-3'>
            {isEditing
              ? travelPreferences.map((pref) => {
                  const Icon = pref.icon;
                  const isSelected = selectedPreferences.includes(pref.id);
                  return (
                    <button
                      key={pref.id}
                      type='button'
                      onClick={() => togglePreference(pref.id)}
                      className={`inline-flex items-center gap-2 px-4 py-2.5 rounded-xl border-2 transition-all ${
                        isSelected
                          ? `${pref.color} border-transparent scale-105`
                          : 'border-gray-200 hover:border-gray-300 bg-white'
                      }`}
                    >
                      <Icon className='w-4 h-4' />
                      <span className='text-sm'>{pref.label}</span>
                    </button>
                  );
                })
              : selectedPrefsData.map((pref) => {
                  const Icon = pref.icon;
                  return (
                    <Badge
                      key={pref.id}
                      className={`${pref.color} border-0 px-4 py-2`}
                    >
                      <Icon className='w-4 h-4 mr-2' />
                      {pref.label}
                    </Badge>
                  );
                })}
          </div>
        </div>

        {/* Appearance Settings */}
        <div className='bg-white dark:bg-card rounded-2xl shadow-sm p-6'>
          <h3 className='mb-4 dark:text-foreground'>Giao diện</h3>
          <div className='flex items-center justify-between'>
            <div className='flex items-center gap-3'>
              {theme === 'dark' ? (
                <Moon className='w-5 h-5 text-[#0066FF]' />
              ) : (
                <Sun className='w-5 h-5 text-[#0066FF]' />
              )}
              <div>
                <p className='font-medium'>
                  Chế độ {theme === 'dark' ? 'tối' : 'sáng'}
                </p>
                <p className='text-sm text-muted-foreground'>
                  Chuyển đổi giữa chế độ sáng và tối
                </p>
              </div>
            </div>
            <button
              onClick={toggleTheme}
              className='relative inline-flex h-11 w-20 items-center rounded-full bg-gray-200 transition-colors hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600'
              aria-label='Toggle theme'
            >
              <span
                className={`inline-block h-9 w-9 transform rounded-full bg-white transition-transform ${
                  theme === 'dark' ? 'translate-x-10' : 'translate-x-1'
                }`}
              >
                {theme === 'dark' ? (
                  <Moon className='w-5 h-5 m-2 text-[#0066FF]' />
                ) : (
                  <Sun className='w-5 h-5 m-2 text-[#0066FF]' />
                )}
              </span>
            </button>
          </div>
        </div>

        {/* Travel History */}
        <div className='bg-white dark:bg-card rounded-2xl shadow-sm p-6'>
          <h3 className='mb-4 dark:text-foreground'>
            Lịch sử tìm kiếm gần đây
          </h3>
          {isLoadingConversations ? (
            <div className='text-center py-8 text-muted-foreground'>
              Đang tải...
            </div>
          ) : conversations.length > 0 ? (
            <div className='space-y-3'>
              {conversations.map((item) => (
                <div
                  key={item.id}
                  className='flex items-start justify-between p-3 rounded-xl hover:bg-accent transition-colors cursor-pointer'
                >
                  <div className='flex-1'>
                    <p className='mb-1'>{item.title}</p>
                    <p className='text-muted-foreground'>
                      {getRelativeTime(item.updated_at || item.created_at)}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className='text-center py-8 text-muted-foreground'>
              Chưa có lịch sử tìm kiếm
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
