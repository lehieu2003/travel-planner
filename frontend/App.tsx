import { useState, useEffect } from 'react';
import {
  Routes,
  Route,
  Navigate,
  useNavigate,
  useLocation,
  useParams,
} from 'react-router-dom';
import { LoginScreen } from './components/LoginScreen';
import { MainLayout } from './components/MainLayout';
import { MultiChatInterface } from './components/MultiChatInterface';
import { SavedItineraries } from './components/SavedItineraries';
import { SavedItineraryDetail } from './components/SavedItineraryDetail';
import { Profile } from './components/Profile';
import { getAuthToken, removeAuthToken, API_ENDPOINTS } from './config/api';
import { Toaster } from './components/ui/sonner';

type Tab = 'chat' | 'itineraries' | 'profile';

// Protected Route Component
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const [isLoggedIn, setIsLoggedIn] = useState<boolean | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const checkAuth = async () => {
      const token = getAuthToken();
      if (!token) {
        setIsLoggedIn(false);
        navigate('/login', { replace: true });
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
          navigate('/login', { replace: true });
        }
      } catch (error) {
        console.error('Error verifying token:', error);
        // Nếu có lỗi mạng, vẫn cho phép sử dụng token tạm thời
        setIsLoggedIn(true);
      }
    };

    checkAuth();
  }, [navigate]);

  if (isLoggedIn === null) {
    return (
      <div className='min-h-screen flex items-center justify-center'>
        <div className='text-center'>
          <div className='animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4'></div>
          <p className='text-muted-foreground'>Đang kiểm tra đăng nhập...</p>
        </div>
      </div>
    );
  }

  return isLoggedIn ? <>{children}</> : null;
}

// Wrapper for Itinerary Detail to use useParams
function ItineraryDetailRoute() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  return (
    <SavedItineraryDetail
      itineraryId={id || ''}
      onBack={() => navigate('/itineraries')}
    />
  );
}

export default function App() {
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogin = () => {
    navigate('/chat');
  };

  const handleLogout = () => {
    removeAuthToken();
    navigate('/login');
  };

  const handleTabChange = (tab: Tab) => {
    navigate(`/${tab}`);
  };

  const handleViewItineraryDetail = (tripId: string) => {
    navigate(`/itineraries/${tripId}`);
  };

  const handleBackToItineraries = () => {
    navigate('/itineraries');
  };

  // Determine active tab from current path
  const getActiveTab = (): Tab => {
    const path = location.pathname;
    if (path.startsWith('/itineraries')) return 'itineraries';
    if (path.startsWith('/profile')) return 'profile';
    return 'chat';
  };

  return (
    <>
      <Routes>
        {/* Public Routes */}
        <Route path='/login' element={<LoginScreen onLogin={handleLogin} />} />

        {/* Protected Routes */}
        <Route
          path='/chat'
          element={
            <ProtectedRoute>
              <MultiChatInterface
                onNavigate={handleTabChange}
                onLogout={handleLogout}
              />
            </ProtectedRoute>
          }
        />

        <Route
          path='/itineraries'
          element={
            <ProtectedRoute>
              <MainLayout
                activeTab='itineraries'
                onTabChange={handleTabChange}
                onLogout={handleLogout}
              >
                <SavedItineraries onViewDetail={handleViewItineraryDetail} />
              </MainLayout>
            </ProtectedRoute>
          }
        />

        <Route
          path='/itineraries/:id'
          element={
            <ProtectedRoute>
              <ItineraryDetailRoute />
            </ProtectedRoute>
          }
        />

        <Route
          path='/profile'
          element={
            <ProtectedRoute>
              <MainLayout
                activeTab='profile'
                onTabChange={handleTabChange}
                onLogout={handleLogout}
              >
                <Profile />
              </MainLayout>
            </ProtectedRoute>
          }
        />

        {/* Default Redirect */}
        <Route
          path='/'
          element={
            getAuthToken() ? (
              <Navigate to='/chat' replace />
            ) : (
              <Navigate to='/login' replace />
            )
          }
        />

        {/* Catch all - redirect to home */}
        <Route path='*' element={<Navigate to='/' replace />} />
      </Routes>
      <Toaster />
    </>
  );
}
