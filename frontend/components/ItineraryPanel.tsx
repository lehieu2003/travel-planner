import {
  MapPin,
  Clock,
  Star,
  Utensils,
  Mountain,
  Coffee,
  X,
  Bookmark,
  Share2,
  Map,
  DollarSign,
  Navigation,
} from 'lucide-react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { ImageWithFallback } from './figma/ImageWithFallback';
import type { ItineraryData } from './ChatMessage';
import { API_ENDPOINTS, getAuthHeaders } from '../config/api';
import { toast } from 'sonner';

interface ItineraryPanelProps {
  itineraryData?: ItineraryData;
  onClose: () => void;
  onSaveSuccess?: () => void;
}

const getActivityIcon = (icon: string) => {
  switch (icon) {
    case 'food':
      return <Utensils className='w-5 h-5' />;
    case 'nature':
      return <Mountain className='w-5 h-5' />;
    case 'coffee':
    case 'drink':
      return <Coffee className='w-5 h-5' />;
    case 'culture':
      return <MapPin className='w-5 h-5' />;
    case 'hotel':
      return <MapPin className='w-5 h-5' />;
    default:
      return <MapPin className='w-5 h-5' />;
  }
};

export function ItineraryPanel({
  itineraryData,
  onClose,
  onSaveSuccess,
}: ItineraryPanelProps) {
  // Debug: log itinerary data
  console.log('ItineraryPanel received data:', {
    hasData: !!itineraryData,
    hasDays: !!itineraryData?.days,
    daysCount: itineraryData?.days?.length || 0,
    days: itineraryData?.days,
  });

  if (!itineraryData) {
    return (
      <div className='h-full flex items-center justify-center p-4'>
        <p className='text-muted-foreground'>Chưa có lịch trình</p>
      </div>
    );
  }

  if (!itineraryData.days || itineraryData.days.length === 0) {
    return (
      <div className='h-full flex items-center justify-center p-4'>
        <p className='text-muted-foreground'>Lịch trình chưa có ngày nào</p>
      </div>
    );
  }

  const handleSave = async () => {
    if (!itineraryData) return;

    try {
      // Generate title from destination and duration
      const title = `${itineraryData.destination} - ${itineraryData.duration}`;

      // Prepare payload with all itinerary data
      const payload = {
        destination: itineraryData.destination,
        duration: itineraryData.duration,
        budget: itineraryData.budget,
        days: itineraryData.days,
        hotel: itineraryData.hotel,
        // Include budget_min and budget_max if available
        budget_min: (itineraryData as any).budget_min,
        budget_max: (itineraryData as any).budget_max,
        // Include categorized places if available
        categorized_places: (itineraryData as any).categorized_places,
      };

      const response = await fetch(API_ENDPOINTS.ITINERARIES.SAVE, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          title,
          payload,
        }),
      });

      if (response.status === 409) {
        // Duplicate itinerary
        toast.info('Bạn đã lưu lịch trình này rồi!');
        return;
      }

      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => ({ detail: 'Lỗi không xác định' }));
        throw new Error(errorData.detail || 'Không thể lưu lịch trình');
      }

      // Success
      toast.success('🎉 Lưu thành công vào Lịch trình đã lưu!');

      // Dispatch custom event to notify other components
      window.dispatchEvent(new CustomEvent('itinerarySaved'));

      // Notify parent component to refresh data
      onSaveSuccess?.();
    } catch (error) {
      console.error('Error saving itinerary:', error);
      toast.error(
        error instanceof Error ? error.message : 'Không thể lưu lịch trình',
      );
    }
  };

  return (
    <div className='h-full flex flex-col'>
      {/* Header */}
      <div className='border-b border-border p-4 flex items-center justify-between bg-white dark:bg-card sticky top-0 z-10'>
        <div className='flex items-center gap-2'>
          <MapPin className='w-5 h-5 text-[#0066FF]' />
          <h3>Lịch trình gợi ý cho bạn</h3>
        </div>
        <button
          onClick={onClose}
          className='lg:hidden p-2 hover:bg-accent rounded-lg transition-colors'
        >
          <X className='w-5 h-5' />
        </button>
      </div>

      {/* Content */}
      <div className='flex-1 overflow-y-auto p-4 sm:p-6 space-y-6'>
        {/* Trip Summary */}
        <div className='bg-gradient-to-br from-[#0066FF]/10 to-[#00C29A]/10 rounded-2xl p-4'>
          <h2 className='mb-3 text-lg font-semibold'>
            {itineraryData.destination}
          </h2>

          {/* Duration and Budget Cards */}
          <div className='flex flex-wrap gap-2'>
            {/* Duration Card */}
            <div className='bg-white dark:bg-card rounded-lg px-3 py-2 shadow-sm border border-border/50 flex items-center gap-2 flex-1 min-w-[140px]'>
              <div className='w-8 h-8 rounded-lg bg-[#0066FF]/10 flex items-center justify-center flex-shrink-0'>
                <Clock className='w-4 h-4 text-[#0066FF]' />
              </div>
              <div className='flex-1 min-w-0'>
                <p className='text-[10px] text-muted-foreground leading-tight'>
                  Thời lượng
                </p>
                <p className='text-sm font-semibold text-foreground truncate leading-tight'>
                  {itineraryData.duration}
                </p>
              </div>
            </div>

            {/* Budget Card */}
            <div className='bg-white dark:bg-card rounded-lg px-3 py-2 shadow-sm border border-border/50 flex items-center gap-2 flex-1 min-w-[140px]'>
              <div className='w-8 h-8 rounded-lg bg-amber-100 flex items-center justify-center flex-shrink-0'>
                <DollarSign className='w-4 h-4 text-amber-600' />
              </div>
              <div className='flex-1 min-w-0'>
                <p className='text-[10px] text-muted-foreground leading-tight'>
                  Ngân sách
                </p>
                <p className='text-sm font-semibold text-foreground truncate leading-tight'>
                  {itineraryData.budget}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Days */}
        {itineraryData.days.map((day) => (
          <div key={day.day} className='space-y-3'>
            <div className='flex items-center gap-3'>
              <div className='w-10 h-10 rounded-full bg-[#0066FF] text-white flex items-center justify-center'>
                {day.day}
              </div>
              <div>
                <h4>Ngày {day.day}</h4>
                <p className='text-muted-foreground'>{day.date}</p>
              </div>
            </div>

            <div className='space-y-2 ml-5 border-l-2 border-[#0066FF]/20 pl-5'>
              {day.activities.length === 0 ? (
                <div className='bg-muted/50 rounded-xl border border-dashed border-border p-4 text-center text-muted-foreground text-sm'>
                  Chưa có hoạt động được lên kế hoạch cho ngày này
                </div>
              ) : (
                day.activities.map((activity) => (
                  <div
                    key={activity.id}
                    className='bg-white dark:bg-card rounded-xl border border-border p-4 hover:shadow-md transition-shadow'
                  >
                    <div className='flex items-start gap-3'>
                      <div className='w-10 h-10 rounded-xl bg-[#00C29A]/10 text-[#00C29A] flex items-center justify-center flex-shrink-0'>
                        {getActivityIcon(activity.icon)}
                      </div>
                      <div className='flex-1 min-w-0'>
                        <h4 className='mb-2 font-semibold'>{activity.name}</h4>

                        {/* Address */}
                        {activity.address && (
                          <div className='flex items-start gap-1.5 mb-2 text-sm text-muted-foreground'>
                            <MapPin className='w-3.5 h-3.5 mt-0.5 flex-shrink-0' />
                            <span className='line-clamp-2'>
                              {activity.address}
                            </span>
                          </div>
                        )}

                        {/* Details Row */}
                        <div className='flex flex-wrap items-center gap-2 text-sm text-muted-foreground'>
                          <span className='flex items-center gap-1'>
                            <Clock className='w-3.5 h-3.5' />
                            {activity.time}
                          </span>
                          <span>•</span>
                          <span>{activity.duration}</span>
                          {activity.travelTime && (
                            <>
                              <span>•</span>
                              <span className='flex items-center gap-1'>
                                <Navigation className='w-3.5 h-3.5' />
                                {activity.travelTime}
                              </span>
                            </>
                          )}
                          {activity.rating && (
                            <>
                              <span>•</span>
                              <span className='flex items-center gap-1'>
                                <Star className='w-3.5 h-3.5 fill-yellow-400 text-yellow-400' />
                                {activity.rating.toFixed(1)}
                              </span>
                            </>
                          )}
                          {activity.cost && (
                            <>
                              <span>•</span>
                              <span className='flex items-center gap-1 text-[#0066FF] font-medium'>
                                <DollarSign className='w-3.5 h-3.5' />
                                {activity.cost}
                              </span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        ))}

        {/* Hotel Recommendation */}
        {itineraryData.hotel && (
          <div className='border-t border-border pt-6'>
            <h3 className='mb-3'>🏨 Khách sạn gợi ý</h3>
            <div className='bg-white dark:bg-card rounded-2xl border border-border overflow-hidden hover:shadow-lg transition-shadow'>
              {itineraryData.hotel.image && (
                <div className='aspect-video relative'>
                  <ImageWithFallback
                    src={itineraryData.hotel.image}
                    alt={itineraryData.hotel.name}
                    className='w-full h-full object-cover'
                  />
                </div>
              )}
              <div className='p-4'>
                <div className='flex items-start justify-between mb-2'>
                  <h4>{itineraryData.hotel.name}</h4>
                  {itineraryData.hotel.rating && (
                    <Badge variant='secondary' className='ml-2'>
                      <Star className='w-3 h-3 fill-yellow-400 text-yellow-400 mr-1' />
                      {itineraryData.hotel.rating}
                    </Badge>
                  )}
                </div>
                <p className='text-[#0066FF] mb-3'>
                  {itineraryData.hotel.price}{' '}
                  {itineraryData.hotel.price.includes('VNĐ') ? '' : 'VNĐ'}
                </p>
                <Button variant='outline' className='w-full rounded-xl'>
                  Xem chi tiết
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className='sticky bottom-0 bg-white dark:bg-card pt-4 pb-2 border-t border-border -mx-4 sm:-mx-6 px-4 sm:px-6 space-y-2'>
          {/* Primary Save Button */}
          <Button
            onClick={handleSave}
            className='w-full rounded-xl bg-[#0066FF] hover:bg-[#0052CC] text-white font-medium'
          >
            <Bookmark className='w-4 h-4 mr-2' />
            Lưu
          </Button>
        </div>
      </div>
    </div>
  );
}
