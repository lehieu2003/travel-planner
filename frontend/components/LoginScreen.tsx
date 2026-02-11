import { useState } from 'react';
import {
  Plane,
  Mail,
  Lock,
  Camera,
  Coffee,
  Mountain,
  Landmark,
  UtensilsCrossed,
  Waves,
  Moon,
  Leaf,
  MapPin,
  ArrowLeft,
  Check,
} from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Slider } from './ui/slider';
import { API_ENDPOINTS, setAuthToken } from '../config/api';

interface LoginScreenProps {
  onLogin: () => void;
}

type Gender = 'male' | 'female' | 'other' | null;
type EnergyLevel = 'low' | 'medium' | 'high' | null;

interface TravelPreference {
  id: string;
  label: string;
  icon: React.ReactNode;
  color: string;
}

const travelPreferences: TravelPreference[] = [
  {
    id: 'photography',
    label: 'Chụp hình',
    icon: <Camera className='w-4 h-4' />,
    color: 'bg-yellow-100 text-yellow-700 border-yellow-200',
  },
  {
    id: 'coffee',
    label: 'Cà phê',
    icon: <Coffee className='w-4 h-4' />,
    color: 'bg-amber-100 text-amber-700 border-amber-200',
  },
  {
    id: 'drink',
    label: 'Đồ uống',
    icon: <Coffee className='w-4 h-4' />,
    color: 'bg-amber-100 text-amber-700 border-amber-200',
  },
  {
    id: 'trekking',
    label: 'Trekking',
    icon: <Mountain className='w-4 h-4' />,
    color: 'bg-green-100 text-green-700 border-green-200',
  },
  {
    id: 'museum',
    label: 'Bảo tàng / Nghệ thuật',
    icon: <Landmark className='w-4 h-4' />,
    color: 'bg-purple-100 text-purple-700 border-purple-200',
  },
  {
    id: 'food',
    label: 'Ẩm thực địa phương',
    icon: <UtensilsCrossed className='w-4 h-4' />,
    color: 'bg-orange-100 text-orange-700 border-orange-200',
  },
  {
    id: 'beach',
    label: 'Biển / nghỉ dưỡng',
    icon: <Waves className='w-4 h-4' />,
    color: 'bg-cyan-100 text-cyan-700 border-cyan-200',
  },
  {
    id: 'nightlife',
    label: 'Nightlife',
    icon: <Moon className='w-4 h-4' />,
    color: 'bg-indigo-100 text-indigo-700 border-indigo-200',
  },
  {
    id: 'relaxed',
    label: 'Chill style',
    icon: <Leaf className='w-4 h-4' />,
    color: 'bg-teal-100 text-teal-700 border-teal-200',
  },
  {
    id: 'culture',
    label: 'Khám phá văn hóa',
    icon: <MapPin className='w-4 h-4' />,
    color: 'bg-pink-100 text-pink-700 border-pink-200',
  },
];

export function LoginScreen({ onLogin }: LoginScreenProps) {
  const [isRegister, setIsRegister] = useState(false);
  const [registrationStep, setRegistrationStep] = useState(1);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Step 2 fields
  const [age, setAge] = useState('');
  const [gender, setGender] = useState<Gender>(null);
  const [energyLevel, setEnergyLevel] = useState<EnergyLevel>(null);
  const [budgetRange, setBudgetRange] = useState<[number, number]>([5, 10]);
  const [selectedPreferences, setSelectedPreferences] = useState<string[]>([]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (isRegister && registrationStep === 1) {
      // Move to step 2
      setRegistrationStep(2);
      return;
    }

    setIsLoading(true);
    try {
      if (isRegister) {
        // Complete registration
        const response = await fetch(API_ENDPOINTS.AUTH.REGISTER, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            email,
            password,
            full_name: fullName || null,
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
          let errorMessage = 'Đăng ký thất bại';
          try {
            const errorData = await response.json();
            errorMessage = errorData.detail || errorMessage;
          } catch {
            errorMessage = `Lỗi ${response.status}: ${response.statusText}`;
          }
          throw new Error(errorMessage);
        }

        let data;
        try {
          data = await response.json();
        } catch (parseError) {
          throw new Error('Không thể đọc phản hồi từ server');
        }

        if (!data.access_token) {
          throw new Error('Không nhận được token từ server');
        }

        setAuthToken(data.access_token);
        onLogin();
      } else {
        // Login
        const response = await fetch(API_ENDPOINTS.AUTH.LOGIN, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            email,
            password,
          }),
        });

        if (!response.ok) {
          let errorMessage = 'Đăng nhập thất bại';
          try {
            const errorData = await response.json();
            errorMessage = errorData.detail || errorMessage;
          } catch {
            errorMessage = `Lỗi ${response.status}: ${response.statusText}`;
          }
          throw new Error(errorMessage);
        }

        let data;
        try {
          data = await response.json();
        } catch (parseError) {
          throw new Error('Không thể đọc phản hồi từ server');
        }

        if (!data.access_token) {
          throw new Error('Không nhận được token từ server');
        }

        setAuthToken(data.access_token);
        onLogin();
      }
    } catch (err) {
      let errorMessage = 'Có lỗi xảy ra';
      if (err instanceof Error) {
        errorMessage = err.message;
      } else if (typeof err === 'string') {
        errorMessage = err;
      }

      // Kiểm tra nếu là lỗi network
      if (
        errorMessage.includes('Failed to fetch') ||
        errorMessage.includes('NetworkError')
      ) {
        errorMessage =
          'Không thể kết nối đến server. Vui lòng kiểm tra kết nối mạng.';
      }

      setError(errorMessage);
      console.error('Login/Register error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleBack = () => {
    setRegistrationStep(1);
  };

  const togglePreference = (id: string) => {
    setSelectedPreferences((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id],
    );
  };

  const switchToLogin = () => {
    setIsRegister(false);
    setRegistrationStep(1);
  };

  const switchToRegister = () => {
    setIsRegister(true);
    setRegistrationStep(1);
  };

  // Step 1: Email & Password
  const renderStep1 = () => (
    <div className='bg-white dark:bg-card rounded-2xl shadow-lg p-8'>
      <h2 className='mb-2'>
        {isRegister ? 'Tạo tài khoản mới' : 'Chào mừng trở lại'}
      </h2>
      <p className='text-muted-foreground mb-6'>
        {isRegister
          ? 'Đăng ký để bắt đầu lên kế hoạch'
          : 'Đăng nhập để tiếp tục'}
      </p>

      {isRegister && (
        <div className='mb-6'>
          <div className='flex items-center gap-2'>
            <div className='flex items-center gap-2 flex-1'>
              <div className='w-8 h-8 rounded-full bg-[#0066FF] text-white flex items-center justify-center'>
                1
              </div>
              <span>Tài khoản</span>
            </div>
            <div className='flex-1 h-0.5 bg-gray-200 dark:bg-border' />
            <div className='flex items-center gap-2 flex-1'>
              <div className='w-8 h-8 rounded-full bg-gray-200 dark:bg-muted text-gray-400 dark:text-muted-foreground flex items-center justify-center'>
                2
              </div>
              <span className='text-muted-foreground'>Sở thích</span>
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className='mb-4 p-3 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 text-sm'>
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className='space-y-4'>
        {isRegister && (
          <div>
            <Label htmlFor='fullName'>Họ và tên</Label>
            <div className='relative mt-1.5'>
              <Input
                id='fullName'
                type='text'
                placeholder='Nguyễn Văn A'
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className='h-11 rounded-xl'
              />
            </div>
          </div>
        )}

        <div>
          <Label htmlFor='email'>Email</Label>
          <div className='relative mt-1.5'>
            <Mail className='absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground' />
            <Input
              id='email'
              type='email'
              placeholder='your@email.com'
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className='pl-10 h-11 rounded-xl'
              required
            />
          </div>
        </div>

        <div>
          <Label htmlFor='password'>Mật khẩu</Label>
          <div className='relative mt-1.5'>
            <Lock className='absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground' />
            <Input
              id='password'
              type='password'
              placeholder='••••••••'
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className='pl-10 h-11 rounded-xl'
              required
            />
          </div>
        </div>

        {!isRegister && (
          <div className='text-right'>
            <button type='button' className='text-[#0066FF] hover:underline'>
              Quên mật khẩu?
            </button>
          </div>
        )}

        <Button
          type='submit'
          className='w-full h-11 rounded-xl bg-[#0066FF] hover:bg-[#0052CC]'
          disabled={isLoading}
        >
          {isLoading ? 'Đang xử lý...' : isRegister ? 'Tiếp tục' : 'Đăng nhập'}
        </Button>
      </form>

      <div className='mt-6 text-center'>
        <button
          type='button'
          onClick={() => (isRegister ? switchToLogin() : switchToRegister())}
          className='text-muted-foreground'
        >
          {isRegister ? (
            <>
              Đã có tài khoản?{' '}
              <span className='text-[#0066FF]'>Đăng nhập ngay</span>
            </>
          ) : (
            <>
              Chưa có tài khoản?{' '}
              <span className='text-[#0066FF]'>Đăng ký ngay</span>
            </>
          )}
        </button>
      </div>
    </div>
  );

  // Step 2: Personal Info & Preferences
  const renderStep2 = () => (
    <div className='w-full'>
      {/* Progress Indicator */}
      <div className='bg-white dark:bg-card rounded-2xl shadow-lg p-6 mb-6'>
        <div className='flex items-center gap-2'>
          <div className='flex items-center gap-2 flex-1'>
            <div className='w-8 h-8 rounded-full bg-[#00C29A] text-white flex items-center justify-center'>
              <Check className='w-5 h-5' />
            </div>
            <span className='text-[#00C29A]'>Tài khoản</span>
          </div>
          <div className='flex-1 h-0.5 bg-[#0066FF]' />
          <div className='flex items-center gap-2 flex-1'>
            <div className='w-8 h-8 rounded-full bg-[#0066FF] text-white flex items-center justify-center'>
              2
            </div>
            <span>Sở thích</span>
          </div>
        </div>
      </div>

      {/* Main Form */}
      <div className='grid lg:grid-cols-2 gap-6'>
        {/* Left: Form */}
        <div className='space-y-6'>
          <div className='bg-white dark:bg-card rounded-2xl shadow-lg p-8'>
            <h2 className='mb-2'>
              Hoàn thiện hồ sơ của bạn để TravelGPT hiểu bạn hơn!
            </h2>
            <p className='text-muted-foreground mb-6'>
              Cung cấp thông tin để nhận đề xuất phù hợp nhất
            </p>

            {/* Personal Info Section */}
            <div className='space-y-6'>
              <div>
                <h3 className='mb-4 flex items-center gap-2'>
                  Thông tin cá nhân
                </h3>

                <div className='space-y-4'>
                  {/* Age */}
                  <div>
                    <Label htmlFor='age'>Tuổi</Label>
                    <Input
                      id='age'
                      type='number'
                      placeholder='25'
                      value={age}
                      onChange={(e) => setAge(e.target.value)}
                      className='mt-1.5 h-11 rounded-xl'
                      min='1'
                      max='120'
                    />
                  </div>

                  {/* Gender */}
                  <div>
                    <Label className='mb-3 block'>Giới tính</Label>
                    <div className='grid grid-cols-3 gap-3'>
                      <button
                        type='button'
                        onClick={() => setGender('male')}
                        className={`h-11 rounded-xl border-2 transition-all ${
                          gender === 'male'
                            ? 'border-[#0066FF] bg-[#0066FF]/5 text-[#0066FF]'
                            : 'border-gray-200 dark:border-border hover:border-gray-300 dark:hover:border-border'
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
                            : 'border-gray-200 dark:border-border hover:border-gray-300 dark:hover:border-border'
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
                            : 'border-gray-200 dark:border-border hover:border-gray-300 dark:hover:border-border'
                        }`}
                      >
                        Khác
                      </button>
                    </div>
                  </div>

                  {/* Energy Level */}
                  <div>
                    <Label className='mb-1.5 block'>Mức năng lượng</Label>
                    <p className='text-sm text-muted-foreground mb-3'>
                      Dùng để phân bổ số lượng hoạt động mỗi ngày.
                    </p>
                    <div className='grid grid-cols-3 gap-3'>
                      <button
                        type='button'
                        onClick={() => setEnergyLevel('low')}
                        className={`h-11 rounded-xl border-2 transition-all ${
                          energyLevel === 'low'
                            ? 'border-[#0066FF] bg-[#0066FF]/5 text-[#0066FF]'
                            : 'border-gray-200 dark:border-border hover:border-gray-300 dark:hover:border-border'
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
                            : 'border-gray-200 dark:border-border hover:border-gray-300 dark:hover:border-border'
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
                            : 'border-gray-200 dark:border-border hover:border-gray-300 dark:hover:border-border'
                        }`}
                      >
                        Cao
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              {/* Travel Preferences Section */}
              <div>
                <h3 className='mb-4'>Sở thích du lịch</h3>
                <p className='text-sm text-muted-foreground mb-4'>
                  Chọn nhiều tùy chọn mà bạn quan tâm
                </p>

                <div className='flex flex-wrap gap-2'>
                  {travelPreferences.map((pref) => (
                    <button
                      key={pref.id}
                      type='button'
                      onClick={() => togglePreference(pref.id)}
                      className={`inline-flex items-center gap-2 px-4 py-2.5 rounded-xl border-2 transition-all ${
                        selectedPreferences.includes(pref.id)
                          ? 'border-[#0066FF] bg-[#0066FF] text-white scale-105'
                          : 'border-gray-200 dark:border-border hover:border-gray-300 dark:hover:border-border bg-white dark:bg-card'
                      }`}
                    >
                      {pref.icon}
                      <span className='text-sm'>{pref.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Budget Range */}
              <div>
                <h3 className='mb-2'>Phạm vi ngân sách</h3>
                <p className='text-sm text-muted-foreground mb-4'>
                  Ngân sách tham khảo, có thể thay đổi khi lập lịch trình
                </p>
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
                  />
                </div>
                <div className='flex justify-between text-sm text-muted-foreground'>
                  <span>1M</span>
                  <span>20M</span>
                </div>
              </div>

              {/* CTA Buttons */}
              <div className='flex gap-3 pt-4'>
                <Button
                  type='button'
                  onClick={handleBack}
                  variant='outline'
                  className='flex-1 h-11 rounded-xl'
                >
                  <ArrowLeft className='w-4 h-4 mr-2' />
                  Quay lại
                </Button>
                <Button
                  type='button'
                  onClick={handleSubmit}
                  className='flex-1 h-11 rounded-xl bg-[#0066FF] hover:bg-[#0052CC]'
                  disabled={isLoading}
                >
                  {isLoading ? 'Đang xử lý...' : 'Hoàn tất đăng ký'}
                </Button>
              </div>
            </div>
          </div>
        </div>

        {/* Right: Illustration */}
        <div className='hidden lg:flex items-center justify-center'>
          <div className='relative'>
            <div className='absolute inset-0 bg-gradient-to-br from-[#0066FF]/20 to-[#00C29A]/20 rounded-3xl blur-3xl' />
            <img
              src='https://images.unsplash.com/photo-1669403337637-edb9a3331fd4?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxoYXBweSUyMHRyYXZlbGVyJTIwYmFja3BhY2slMjBhZHZlbnR1cmV8ZW58MXx8fHwxNzY1NTIyNzgzfDA&ixlib=rb-4.1.0&q=80&w=1080&utm_source=figma&utm_medium=referral'
              alt='Travel illustration'
              className='relative rounded-3xl shadow-2xl w-full max-w-md object-cover'
            />
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className='min-h-screen flex flex-col lg:flex-row bg-[#F8FAFC] dark:bg-background'>
      {/* Left side - Hero/Illustration (only show on step 1) */}
      {(!isRegister || registrationStep === 1) && (
        <div className='hidden lg:flex lg:w-1/2 bg-gradient-to-br from-[#0066FF] to-[#00C29A] p-12 items-center justify-center relative overflow-hidden'>
          <div className='absolute inset-0 opacity-10'>
            <svg
              className='w-full h-full'
              viewBox='0 0 100 100'
              preserveAspectRatio='none'
            >
              <defs>
                <pattern
                  id='grid'
                  width='10'
                  height='10'
                  patternUnits='userSpaceOnUse'
                >
                  <path
                    d='M 10 0 L 0 0 0 10'
                    fill='none'
                    stroke='white'
                    strokeWidth='0.5'
                  />
                </pattern>
              </defs>
              <rect width='100' height='100' fill='url(#grid)' />
            </svg>
          </div>

          <div className='relative z-10 text-white text-center'>
            <div className='w-32 h-32 mx-auto mb-8 bg-white/20 rounded-3xl backdrop-blur-sm flex items-center justify-center'>
              <Plane className='w-16 h-16' strokeWidth={1.5} />
            </div>
            <h1 className='mb-4'>TravelBuddy</h1>
            <p className='text-white/90 max-w-md mx-auto'>
              Your smart AI travel companion for planning unforgettable
              adventures. Get personalized itineraries in seconds.
            </p>
          </div>
        </div>
      )}

      {/* Right side - Form */}
      <div
        className={`flex-1 flex items-center justify-center p-6 lg:p-12 ${isRegister && registrationStep === 2 ? 'lg:col-span-2' : ''}`}
      >
        <div
          className={`w-full ${isRegister && registrationStep === 2 ? 'max-w-6xl' : 'max-w-md'}`}
        >
          {/* Mobile Logo */}
          <div className='lg:hidden mb-8 text-center'>
            <div className='w-16 h-16 mx-auto mb-4 bg-gradient-to-br from-[#0066FF] to-[#00C29A] rounded-2xl flex items-center justify-center'>
              <Plane className='w-8 h-8 text-white' />
            </div>
            <h2 className='text-[#0066FF]'>TravelBuddy</h2>
          </div>

          {isRegister && registrationStep === 2 ? renderStep2() : renderStep1()}
        </div>
      </div>
    </div>
  );
}
