import { useState, useEffect } from 'react';
import { Calendar, MapPin, Clock } from 'lucide-react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { ImageWithFallback } from './figma/ImageWithFallback';
import { API_ENDPOINTS, getAuthHeaders } from '../config/api';

interface SavedItinerary {
  id: number;
  title: string;
  payload: {
    destination: string;
    duration: string;
    budget: string;
    days?: Array<{
      day: number;
      date: string;
      activities: Array<any>;
    }>;
    hotel?: {
      name: string;
      image?: string;
    };
  };
  created_at: string;
}

interface SavedItinerariesProps {
  onViewDetail?: (itineraryId: string) => void;
}

export function SavedItineraries({ onViewDetail }: SavedItinerariesProps) {
  const [itineraries, setItineraries] = useState<SavedItinerary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadItineraries();
  }, []);

  // Listen for itinerary saved event to refresh list
  useEffect(() => {
    const handleItinerarySaved = () => {
      loadItineraries();
    };

    window.addEventListener('itinerarySaved', handleItinerarySaved);
    return () => {
      window.removeEventListener('itinerarySaved', handleItinerarySaved);
    };
  }, []);

  const loadItineraries = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const response = await fetch(API_ENDPOINTS.ITINERARIES.LIST, {
        headers: getAuthHeaders(),
      });

      if (!response.ok) {
        if (response.status === 401) {
          setError('Phiên đăng nhập đã hết hạn');
          return;
        }
        throw new Error('Không thể tải danh sách lịch trình');
      }

      const data = await response.json();
      setItineraries(data.items || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Có lỗi xảy ra');
    } finally {
      setIsLoading(false);
    }
  };

  // Format date from created_at
  const formatDate = (dateStr: string) => {
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('vi-VN', {
        day: 'numeric',
        month: 'long',
      });
    } catch {
      return dateStr;
    }
  };

  // Get dates from itinerary days if available
  const getDates = (itinerary: SavedItinerary) => {
    if (itinerary.payload.days && itinerary.payload.days.length > 0) {
      const firstDay = itinerary.payload.days[0];
      const lastDay = itinerary.payload.days[itinerary.payload.days.length - 1];
      if (firstDay.date && lastDay.date) {
        return `${firstDay.date} - ${lastDay.date}`;
      }
    }
    return formatDate(itinerary.created_at);
  };

  // Get tags from itinerary (simplified - can be enhanced)
  const getTags = (itinerary: SavedItinerary): string[] => {
    const tags: string[] = [];
    if (itinerary.payload.days) {
      itinerary.payload.days.forEach((day) => {
        day.activities?.forEach((activity: any) => {
          if (
            (activity.icon === 'coffee' || activity.icon === 'drink') &&
            !tags.includes('Cafe')
          )
            tags.push('Cafe');
          if (activity.icon === 'food' && !tags.includes('Food'))
            tags.push('Food');
          if (activity.icon === 'nature' && !tags.includes('Nature'))
            tags.push('Nature');
        });
      });
    }
    return tags.length > 0 ? tags : ['Travel'];
  };

  // Get image from hotel or use default
  const getImage = (itinerary: SavedItinerary): string => {
    if (itinerary.payload.hotel?.image) {
      return itinerary.payload.hotel.image;
    }
    // Default image based on destination
    return 'https://images.unsplash.com/photo-1488646953014-85cb44e25828?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080';
  };

  if (isLoading) {
    return (
      <div className='p-4 sm:p-6 lg:p-8'>
        <div className='flex items-center justify-center py-16'>
          <div className='text-center'>
            <div className='animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4'></div>
            <p className='text-muted-foreground'>Đang tải lịch trình...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className='p-4 sm:p-6 lg:p-8'>
        <div className='text-center py-16'>
          <p className='text-red-600 mb-4'>{error}</p>
          <Button
            onClick={loadItineraries}
            className='bg-[#0066FF] hover:bg-[#0052CC] rounded-xl'
          >
            Thử lại
          </Button>
        </div>
      </div>
    );
  }

  const SAVED_TRIPS = itineraries.map((it) => ({
    id: it.id.toString(),
    title: it.title,
    destination: it.payload.destination,
    dates: getDates(it),
    duration: it.payload.duration,
    budget: it.payload.budget,
    image: getImage(it),
    tags: getTags(it),
  }));
  return (
    <div className='p-4 sm:p-6 lg:p-8'>
      <div className='mb-6'>
        <h2 className='mb-2'>Lịch trình đã lưu</h2>
        <p className='text-muted-foreground'>
          Quản lý các chuyến du lịch bạn đã lên kế hoạch
        </p>
      </div>

      {SAVED_TRIPS.length === 0 ? (
        <div className='text-center py-16'>
          <div className='w-20 h-20 mx-auto mb-4 bg-muted dark:bg-muted rounded-full flex items-center justify-center'>
            <Calendar className='w-10 h-10 text-muted-foreground' />
          </div>
          <h3 className='mb-2'>Chưa có lịch trình nào</h3>
          <p className='text-muted-foreground mb-4'>
            Bắt đầu chat với AI để tạo lịch trình du lịch đầu tiên
          </p>
          <Button className='bg-[#0066FF] hover:bg-[#0052CC] rounded-xl'>
            Tạo lịch trình mới
          </Button>
        </div>
      ) : (
        <div className='grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 lg:gap-6'>
          {SAVED_TRIPS.map((trip) => (
            <div
              key={trip.id}
              className='bg-white dark:bg-card rounded-2xl border border-border overflow-hidden hover:shadow-xl transition-all duration-300 group'
            >
              {/* Image */}
              <div className='aspect-[4/3] relative overflow-hidden'>
                <ImageWithFallback
                  src={trip.image}
                  alt={trip.title}
                  className='w-full h-full object-cover group-hover:scale-105 transition-transform duration-300'
                />
                <div className='absolute top-3 right-3'>
                  <Badge className='bg-white/90 dark:bg-card/90 text-foreground backdrop-blur-sm'>
                    {trip.duration}
                  </Badge>
                </div>
              </div>

              {/* Content */}
              <div className='p-4'>
                <h3 className='mb-2'>{trip.title}</h3>

                <div className='space-y-2 mb-4 text-muted-foreground'>
                  <div className='flex items-center gap-2'>
                    <MapPin className='w-4 h-4 flex-shrink-0' />
                    <span>{trip.destination}</span>
                  </div>
                  <div className='flex items-center gap-2'>
                    <Calendar className='w-4 h-4 flex-shrink-0' />
                    <span>{trip.dates}</span>
                  </div>
                  <div className='flex items-center gap-2'>
                    <Clock className='w-4 h-4 flex-shrink-0' />
                    <span className='text-[#0066FF]'>{trip.budget}</span>
                  </div>
                </div>

                {/* Tags */}
                <div className='flex flex-wrap gap-1.5 mb-4'>
                  {trip.tags.map((tag) => (
                    <Badge
                      key={tag}
                      variant='secondary'
                      className='bg-[#0066FF]/10 text-[#0066FF] border-0'
                    >
                      {tag}
                    </Badge>
                  ))}
                </div>

                {/* Action Button */}
                <Button
                  className='w-full rounded-xl bg-[#0066FF] hover:bg-[#0052CC]'
                  onClick={() => onViewDetail?.(trip.id)}
                >
                  Xem chi tiết
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
