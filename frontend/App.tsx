import { useState, useEffect } from 'react';
import { LoginScreen } from './components/LoginScreen';
import { MainLayout } from './components/MainLayout';
import { MultiChatInterface } from './components/MultiChatInterface';
import { SavedItineraries } from './components/SavedItineraries';
import { SavedItineraryDetail } from './components/SavedItineraryDetail';
import { Profile } from './components/Profile';
import { getAuthToken, removeAuthToken, API_ENDPOINTS } from './config/api';
import { Toaster } from './components/ui/sonner';
import './styles/globals.css';

type Tab = 'chat' | 'itineraries' | 'profile';

export default function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);
  const [activeTab, setActiveTab] = useState<Tab>('chat');
  const [selectedItineraryId, setSelectedItineraryId] = useState<string | null>(
    null,
  );

  // Kiểm tra authentication khi app khởi động
  useEffect(() => {
    const checkAuth = async () => {
      const token = getAuthToken();
      if (!token) {
        setIsCheckingAuth(false);
        setIsLoggedIn(false);
        return;
      }

      try {
        // Verify token với backend
        const response = await fetch(API_ENDPOINTS.AUTH.ME, {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        });

        if (response.ok) {
          setIsLoggedIn(true);
        } else {
          // Token không hợp lệ, xóa và yêu cầu đăng nhập lại
          removeAuthToken();
          setIsLoggedIn(false);
        }
      } catch (error) {
        console.error('Error verifying token:', error);
        // Nếu có lỗi mạng, vẫn cho phép sử dụng token tạm thời
        setIsLoggedIn(true);
      } finally {
        setIsCheckingAuth(false);
      }
    };

    checkAuth();
  }, []);

  const handleLogin = () => {
    setIsLoggedIn(true);
  };

  const handleLogout = () => {
    removeAuthToken();
    setIsLoggedIn(false);
    setActiveTab('chat');
    setSelectedItineraryId(null);
  };

  const handleTabChange = (tab: Tab) => {
    setActiveTab(tab);
    setSelectedItineraryId(null);
  };

  const handleViewItineraryDetail = (tripId: string) => {
    setSelectedItineraryId(tripId);
  };

  const handleBackToItineraries = () => {
    setSelectedItineraryId(null);
  };

  // Hiển thị loading khi đang kiểm tra authentication
  if (isCheckingAuth) {
    return (
      <div className='min-h-screen flex items-center justify-center'>
        <div className='text-center'>
          <div className='animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4'></div>
          <p className='text-muted-foreground'>Đang kiểm tra đăng nhập...</p>
        </div>
      </div>
    );
  }

  if (!isLoggedIn) {
    return <LoginScreen onLogin={handleLogin} />;
  }

  // Use MultiChatInterface for chat view
  if (activeTab === 'chat') {
    return (
      <>
        <MultiChatInterface
          onNavigate={handleTabChange}
          onLogout={handleLogout}
        />
        <Toaster />
      </>
    );
  }

  // Show itinerary detail if one is selected
  if (activeTab === 'itineraries' && selectedItineraryId) {
    return (
      <SavedItineraryDetail
        itineraryId={selectedItineraryId}
        onBack={handleBackToItineraries}
      />
    );
  }

  // Use MainLayout for other views
  return (
    <>
      <MainLayout
        activeTab={activeTab}
        onTabChange={handleTabChange}
        onLogout={handleLogout}
      >
        {activeTab === 'itineraries' && (
          <SavedItineraries onViewDetail={handleViewItineraryDetail} />
        )}
        {activeTab === 'profile' && <Profile />}
      </MainLayout>
      <Toaster />
    </>
  );
}
