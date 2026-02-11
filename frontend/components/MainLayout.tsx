import { ReactNode, useState, useEffect, useRef } from 'react';
import {
  MessageSquare,
  Calendar,
  User,
  LogOut,
  Menu,
  X,
  Plane,
  BookmarkCheck,
  ChevronDown,
} from 'lucide-react';
import { Avatar, AvatarFallback, AvatarImage } from './ui/avatar';
import { Button } from './ui/button';

interface MainLayoutProps {
  children: ReactNode;
  activeTab: 'chat' | 'itineraries' | 'profile';
  onTabChange: (tab: 'chat' | 'itineraries' | 'profile') => void;
  onLogout: () => void;
}

export function MainLayout({
  children,
  activeTab,
  onTabChange,
  onLogout,
}: MainLayoutProps) {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsDropdownOpen(false);
      }
    };

    if (isDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isDropdownOpen]);

  return (
    <div className='min-h-screen bg-[#F8FAFC] dark:bg-background'>
      {/* Header */}
      <header className='bg-white dark:bg-card border-b border-border sticky top-0 z-50'>
        <div className='max-w-7xl mx-auto px-4 sm:px-6 lg:px-8'>
          <div className='flex items-center justify-between h-16'>
            {/* Logo */}
            <div className='flex items-center gap-3'>
              <button
                className='lg:hidden p-2 -ml-2'
                onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              >
                {isMobileMenuOpen ? (
                  <X className='w-6 h-6' />
                ) : (
                  <Menu className='w-6 h-6' />
                )}
              </button>
              <div className='flex items-center gap-2'>
                <div className='w-9 h-9 bg-gradient-to-br from-[#0066FF] to-[#00C29A] rounded-xl flex items-center justify-center'>
                  <Plane className='w-5 h-5 text-white' />
                </div>
                <span className='hidden sm:block text-[#0066FF]'>
                  Travel Planner Chatbot
                </span>
              </div>
            </div>

            {/* User Menu */}
            <div className='relative z-[100]' ref={dropdownRef}>
              <Button
                variant='ghost'
                className='flex items-center gap-2 hover:bg-muted rounded-xl'
                onClick={() => setIsDropdownOpen(!isDropdownOpen)}
              >
                <Avatar className='w-9 h-9'>
                  <AvatarImage src='https://api.dicebear.com/7.x/avataaars/svg?seed=traveler' />
                  <AvatarFallback>TU</AvatarFallback>
                </Avatar>
                <ChevronDown
                  className={`h-4 w-4 text-muted-foreground transition-transform ${isDropdownOpen ? 'rotate-180' : ''}`}
                />
              </Button>

              {isDropdownOpen && (
                <div className='absolute right-0 top-full mt-2 w-48 rounded-xl bg-white dark:bg-card border shadow-lg z-[100] py-1 animate-in fade-in-0 zoom-in-95'>
                  <button
                    onClick={() => {
                      setIsDropdownOpen(false);
                      onTabChange('chat');
                    }}
                    className='w-full flex items-center gap-2 px-4 py-2 hover:bg-muted rounded-lg cursor-pointer text-left'
                  >
                    <MessageSquare className='h-4 w-4' />
                    Chat với AI
                  </button>
                  <button
                    onClick={() => {
                      setIsDropdownOpen(false);
                      activeTab === 'itineraries'
                        ? onTabChange('profile')
                        : onTabChange('itineraries');
                    }}
                    className='w-full flex items-center gap-2 px-4 py-2 hover:bg-muted rounded-lg cursor-pointer text-left'
                  >
                    {activeTab === 'itineraries' ? (
                      <User className='h-4 w-4' />
                    ) : (
                      <BookmarkCheck className='h-4 w-4' />
                    )}
                    {activeTab === 'itineraries'
                      ? 'Hồ sơ cá nhân'
                      : 'Lịch trình đã lưu'}
                  </button>
                  <div className='h-px bg-border my-1' />
                  <button
                    onClick={() => {
                      setIsDropdownOpen(false);
                      onLogout();
                    }}
                    className='w-full flex items-center gap-2 px-4 py-2 hover:bg-muted rounded-lg cursor-pointer text-left text-destructive'
                  >
                    <LogOut className='h-4 w-4' />
                    Đăng xuất
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Mobile Navigation */}
        {isMobileMenuOpen && (
          <div className='lg:hidden border-t border-border'>
            <nav className='px-4 py-3 space-y-1'>
              <button
                onClick={() => {
                  onTabChange('chat');
                  setIsMobileMenuOpen(false);
                }}
                className={`w-full px-4 py-2.5 rounded-lg transition-colors flex items-center ${
                  activeTab === 'chat'
                    ? 'bg-[#0066FF]/10 text-[#0066FF]'
                    : 'text-foreground/70 hover:text-foreground hover:bg-accent'
                }`}
              >
                <MessageSquare className='w-5 h-5 mr-3' />
                Chat với AI
              </button>
              <button
                onClick={() => {
                  onTabChange('itineraries');
                  setIsMobileMenuOpen(false);
                }}
                className={`w-full px-4 py-2.5 rounded-lg transition-colors flex items-center ${
                  activeTab === 'itineraries'
                    ? 'bg-[#0066FF]/10 text-[#0066FF]'
                    : 'text-foreground/70 hover:text-foreground hover:bg-accent'
                }`}
              >
                <Calendar className='w-5 h-5 mr-3' />
                Lịch trình của tôi
              </button>
              <button
                onClick={() => {
                  onTabChange('profile');
                  setIsMobileMenuOpen(false);
                }}
                className={`w-full px-4 py-2.5 rounded-lg transition-colors flex items-center ${
                  activeTab === 'profile'
                    ? 'bg-[#0066FF]/10 text-[#0066FF]'
                    : 'text-foreground/70 hover:text-foreground hover:bg-accent'
                }`}
              >
                <User className='w-5 h-5 mr-3' />
                Hồ sơ của tôi
              </button>
            </nav>
          </div>
        )}
      </header>

      {/* Main Content */}
      <main className='max-w-7xl mx-auto'>{children}</main>
    </div>
  );
}
