import { useState, useEffect } from 'react';
import {
  ArrowLeft,
  Calendar,
  DollarSign,
  MapPin,
  Clock,
  Star,
  Navigation,
  Trash2,
  Coffee,
  Utensils,
  Mountain,
  Landmark,
  Hotel,
} from 'lucide-react';
import { Button } from './ui/button';
import { API_ENDPOINTS, getAuthHeaders } from '../config/api';

interface SavedItineraryDetailProps {
  itineraryId: string;
  onBack: () => void;
}

interface SavedItinerary {
  id: number;
  title: string;
  payload: {
    destination: string;
    duration: string;
    budget: string;
    budget_min?: number;
    budget_max?: number;
    days?: Array<{
      day: number;
      date: string;
      activities: Array<{
        id: string;
        name: string;
        icon?: string;
        category?: string;
        address?: string;
        time?: string;
        duration?: string;
        rating?: number;
        cost?: string;
        travelTime?: string;
        travelTimeToNext?: string; // Formatted string like "15 phút"
        travelTimeToNextMinutes?: number; // Raw minutes for calculations
        distanceToNext?: number; // Distance in meters
        notes?: string;
        description?: string;
      }>;
    }>;
    hotel?: {
      name: string;
      address?: string;
      price?: string;
      rating?: number;
      image?: string;
    };
    categorized_places?: {
      places?: Array<{
        name: string;
        description?: string;
        address?: string;
        rating?: number;
      }>;
      food?: Array<{
        name: string;
        description?: string;
        address?: string;
        rating?: number;
      }>;
      coffee?: Array<{
        name: string;
        description?: string;
        address?: string;
        rating?: number;
      }>;
      drink?: Array<{
        name: string;
        description?: string;
        address?: string;
        rating?: number;
      }>;
    };
  };
  created_at: string;
}

// Helper function to extract categorized places from days if categorized_places is not available
const extractCategorizedPlaces = (days?: Array<{ activities: Array<any> }>) => {
  const places: Array<{
    name: string;
    description?: string;
    address?: string;
    rating?: number;
  }> = [];
  const food: Array<{
    name: string;
    description?: string;
    address?: string;
    rating?: number;
  }> = [];
  const coffee: Array<{
    name: string;
    description?: string;
    address?: string;
    rating?: number;
  }> = [];
  const drink: Array<{
    name: string;
    description?: string;
    address?: string;
    rating?: number;
  }> = [];

  if (!days) return { places, food, coffee, drink };

  const seenNames = new Set<string>();

  days.forEach((day) => {
    day.activities?.forEach((activity: any) => {
      const name = activity.name?.trim();
      if (!name || seenNames.has(name.toLowerCase())) return;
      seenNames.add(name.toLowerCase());

      const placeInfo = {
        name,
        description: activity.notes || activity.description || '',
        address: activity.address || '',
        rating: activity.rating,
      };

      const category = activity.icon || activity.category || '';
      if (category === 'food' || category === 'restaurant') {
        food.push(placeInfo);
      } else if (
        category === 'drink' ||
        category === 'coffee' ||
        category === 'cafe'
      ) {
        drink.push(placeInfo);
        coffee.push(placeInfo); // Backward compatibility
      } else {
        places.push(placeInfo);
      }
    });
  });

  return { places, food, coffee, drink };
};

const getCategoryIcon = (category: string) => {
  const icons: Record<string, any> = {
    hotel: Hotel,
    food: Utensils,
    coffee: Coffee,
    drink: Coffee,
    nature: Mountain,
    culture: Landmark,
    adventure: Mountain,
  };
  return icons[category] || MapPin;
};

const getCategoryColor = (category: string) => {
  const colors: Record<string, string> = {
    hotel: 'bg-purple-100 text-purple-700',
    food: 'bg-orange-100 text-orange-700',
    coffee: 'bg-amber-100 text-amber-700',
    nature: 'bg-green-100 text-green-700',
    culture: 'bg-blue-100 text-blue-700',
    adventure: 'bg-red-100 text-red-700',
  };
  return colors[category] || 'bg-gray-100 text-gray-700';
};

const getTransportIcon = (mode: string | null) => {
  if (!mode) return null;
  if (mode.includes('bộ')) return '🚶';
  if (mode.includes('máy')) return '🏍️';
  if (mode.includes('taxi') || mode.includes('xe')) return '🚗';
  return '🚌';
};

// Helper function to format duration (minutes to "X phút" or "Y giờ Z phút")
const formatDuration = (durationStr: string): string => {
  // Try to extract minutes from duration string
  const minutesMatch = durationStr.match(/(\d+)\s*phút/);
  if (minutesMatch) {
    const minutes = parseInt(minutesMatch[1]);
    if (minutes < 60) {
      return `${minutes} phút`;
    } else {
      const hours = Math.floor(minutes / 60);
      const remainingMinutes = minutes % 60;
      if (remainingMinutes === 0) {
        return `${hours} giờ`;
      }
      return `${hours} giờ ${remainingMinutes} phút`;
    }
  }

  // Try to extract hours and minutes
  const hoursMatch = durationStr.match(/(\d+)\s*giờ/);
  const minsMatch = durationStr.match(/(\d+)\s*phút/);
  if (hoursMatch && minsMatch) {
    return durationStr; // Already formatted
  }

  // If duration is just a number, assume it's minutes
  const numMatch = durationStr.match(/^(\d+)$/);
  if (numMatch) {
    const minutes = parseInt(numMatch[1]);
    if (minutes < 60) {
      return `${minutes} phút`;
    } else {
      const hours = Math.floor(minutes / 60);
      const remainingMinutes = minutes % 60;
      if (remainingMinutes === 0) {
        return `${hours} giờ`;
      }
      return `${hours} giờ ${remainingMinutes} phút`;
    }
  }

  // Return as is if can't parse
  return durationStr;
};

// Helper function to extract minutes from duration string
const extractMinutes = (durationStr: string): number => {
  // Try to match "X phút" or "Y giờ Z phút" or just number
  const hoursMatch = durationStr.match(/(\d+)\s*giờ/);
  const minutesMatch = durationStr.match(/(\d+)\s*phút/);
  const numMatch = durationStr.match(/^(\d+)$/);

  let totalMinutes = 0;
  if (hoursMatch) {
    totalMinutes += parseInt(hoursMatch[1]) * 60;
  }
  if (minutesMatch) {
    totalMinutes += parseInt(minutesMatch[1]);
  }
  if (numMatch && totalMinutes === 0) {
    // If just a number and no hours/minutes found, assume it's minutes
    totalMinutes = parseInt(numMatch[1]);
  }

  return totalMinutes || 60; // Default to 60 minutes if can't parse
};

// Helper function to calculate duration in minutes from time range
const calculateDurationFromTimeRange = (
  startTime: string,
  endTime: string,
): number => {
  const startMatch = startTime.match(/(\d{1,2}):(\d{2})/);
  const endMatch = endTime.match(/(\d{1,2}):(\d{2})/);

  if (startMatch && endMatch) {
    const startHour = parseInt(startMatch[1]);
    const startMin = parseInt(startMatch[2]);
    const endHour = parseInt(endMatch[1]);
    const endMin = parseInt(endMatch[2]);

    const startTotalMinutes = startHour * 60 + startMin;
    const endTotalMinutes = endHour * 60 + endMin;

    return endTotalMinutes - startTotalMinutes;
  }

  return 0;
};

// Helper function to parse time range and calculate end time if needed
// Returns both time range and calculated duration that matches
const parseTimeRange = (
  timeStr: string | undefined,
  durationStr: string | undefined,
  previousEndTime: string | null = null,
  dayStartTime: string = '09:00',
): {
  startTime: string;
  endTime: string;
  calculatedDurationMinutes: number;
} | null => {
  // If time range is provided (e.g., "14:00 - 15:30" or "14:00 – 15:30")
  if (timeStr) {
    const rangeMatch = timeStr.match(
      /(\d{1,2}):(\d{2})\s*[-–]\s*(\d{1,2}):(\d{2})/,
    );
    if (rangeMatch) {
      const startTime = `${rangeMatch[1].padStart(2, '0')}:${rangeMatch[2]}`;
      const endTime = `${rangeMatch[3].padStart(2, '0')}:${rangeMatch[4]}`;
      const calculatedDuration = calculateDurationFromTimeRange(
        startTime,
        endTime,
      );

      return {
        startTime,
        endTime,
        calculatedDurationMinutes: calculatedDuration,
      };
    }

    // If only start time is provided (e.g., "14:00")
    const singleTimeMatch = timeStr.match(/(\d{1,2}):(\d{2})/);
    if (singleTimeMatch) {
      const startHour = parseInt(singleTimeMatch[1]);
      const startMin = parseInt(singleTimeMatch[2]);
      const startTime = `${startHour.toString().padStart(2, '0')}:${startMin.toString().padStart(2, '0')}`;

      // Calculate end time from duration if available
      if (durationStr) {
        const durationMinutes = extractMinutes(durationStr);
        let endMin = startMin + durationMinutes;
        let endHour = startHour;
        while (endMin >= 60) {
          endHour += 1;
          endMin -= 60;
        }
        if (endHour >= 24) {
          endHour = 23;
          endMin = 59;
        }

        return {
          startTime,
          endTime: `${endHour.toString().padStart(2, '0')}:${endMin.toString().padStart(2, '0')}`,
          calculatedDurationMinutes: durationMinutes,
        };
      }

      // If no duration, assume 1 hour
      const defaultDuration = 60;
      let endMin = startMin + defaultDuration;
      let endHour = startHour;
      if (endMin >= 60) {
        endHour += 1;
        endMin -= 60;
      }
      if (endHour >= 24) {
        endHour = 23;
        endMin = 59;
      }

      return {
        startTime,
        endTime: `${endHour.toString().padStart(2, '0')}:${endMin.toString().padStart(2, '0')}`,
        calculatedDurationMinutes: defaultDuration,
      };
    }
  }

  // If only duration is provided, calculate from previous end time or day start
  if (durationStr) {
    const durationMinutes = extractMinutes(durationStr);
    const baseTime = previousEndTime || dayStartTime;
    const baseMatch = baseTime.match(/(\d{1,2}):(\d{2})/);

    if (baseMatch) {
      const startHour = parseInt(baseMatch[1]);
      const startMin = parseInt(baseMatch[2]);

      let endMin = startMin + durationMinutes;
      let endHour = startHour;
      while (endMin >= 60) {
        endHour += 1;
        endMin -= 60;
      }
      if (endHour >= 24) {
        endHour = 23;
        endMin = 59;
      }

      return {
        startTime: baseTime,
        endTime: `${endHour.toString().padStart(2, '0')}:${endMin.toString().padStart(2, '0')}`,
        calculatedDurationMinutes: durationMinutes,
      };
    }
  }

  return null;
};

export function SavedItineraryDetail({
  itineraryId,
  onBack,
}: SavedItineraryDetailProps) {
  const [itinerary, setItinerary] = useState<SavedItinerary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  useEffect(() => {
    loadItinerary();
  }, [itineraryId]);

  const loadItinerary = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const response = await fetch(
        API_ENDPOINTS.ITINERARIES.GET(parseInt(itineraryId)),
        {
          headers: getAuthHeaders(),
        },
      );

      if (!response.ok) {
        if (response.status === 404) {
          setError('Không tìm thấy lịch trình.');
          return;
        }
        if (response.status === 401) {
          setError('Phiên đăng nhập đã hết hạn');
          return;
        }
        throw new Error('Không thể tải lịch trình');
      }

      const data = await response.json();
      setItinerary(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Có lỗi xảy ra');
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className='min-h-screen bg-[#F8FAFC] flex items-center justify-center'>
        <div className='text-center'>
          <div className='animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4'></div>
          <p className='text-muted-foreground'>Đang tải lịch trình...</p>
        </div>
      </div>
    );
  }

  if (error || !itinerary) {
    return (
      <div className='min-h-screen bg-[#F8FAFC]'>
        <div className='bg-white border-b border-border sticky top-0 z-10'>
          <div className='max-w-7xl mx-auto p-4 sm:p-6'>
            <button
              onClick={onBack}
              className='flex items-center gap-2 text-muted-foreground hover:text-foreground mb-4 transition-colors'
            >
              <ArrowLeft className='w-4 h-4' />
              Quay lại danh sách
            </button>
          </div>
        </div>
        <div className='max-w-7xl mx-auto p-4 sm:p-6'>
          <div className='bg-white rounded-2xl shadow-sm p-8 text-center'>
            <p className='text-lg text-muted-foreground'>
              {error || 'Không tìm thấy lịch trình.'}
            </p>
            <Button onClick={onBack} className='mt-4 rounded-xl'>
              Quay lại danh sách
            </Button>
          </div>
        </div>
      </div>
    );
  }

  const payload = itinerary.payload;
  const categorizedPlaces =
    payload.categorized_places || extractCategorizedPlaces(payload.days);

  // Calculate total days and nights from duration string or days array
  const durationMatch = payload.duration?.match(/(\d+)\s*ngày/);
  const totalDays = durationMatch
    ? parseInt(durationMatch[1])
    : payload.days?.length || 0;
  const totalNights = totalDays > 0 ? totalDays - 1 : 0;

  // Format date created
  const formatDate = (dateStr: string) => {
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('vi-VN', {
        day: 'numeric',
        month: 'long',
        year: 'numeric',
      });
    } catch {
      return dateStr;
    }
  };

  const dateCreated = formatDate(itinerary.created_at);

  // Get trip dates from days if available
  const getTripDates = () => {
    if (payload.days && payload.days.length > 0) {
      const firstDay = payload.days[0];
      const lastDay = payload.days[payload.days.length - 1];
      if (firstDay.date && lastDay.date) {
        return `${firstDay.date} - ${lastDay.date}`;
      }
    }
    return dateCreated;
  };

  const tripDates = getTripDates();

  const handleDelete = () => {
    if (confirm('Bạn có chắc chắn muốn xóa lịch trình này?')) {
      alert('Đã xóa lịch trình');
      onBack();
    }
  };

  return (
    <div className='min-h-screen bg-[#F8FAFC]'>
      {/* Header */}
      <div className='bg-white border-b border-border sticky top-0 z-10'>
        <div className='max-w-7xl mx-auto p-4 sm:p-6'>
          <button
            onClick={onBack}
            className='flex items-center gap-2 text-muted-foreground hover:text-foreground mb-4 transition-colors'
          >
            <ArrowLeft className='w-4 h-4' />
            Quay lại danh sách
          </button>

          <div className='flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4'>
            <div>
              <h1 className='mb-2'>{itinerary.title}</h1>
              <div className='flex flex-wrap items-center gap-3 text-muted-foreground'>
                <span className='flex items-center gap-1.5'>
                  <Calendar className='w-4 h-4' />
                  {tripDates}
                </span>
                <span>•</span>
                <span>
                  {totalDays} ngày {totalNights > 0 ? `${totalNights} đêm` : ''}
                </span>
                <span>•</span>
                <span className='text-sm'>Tạo ngày {dateCreated}</span>
              </div>
            </div>

            {/* Action Buttons */}
            <div className='flex flex-wrap gap-2'>
              <Button
                onClick={handleDelete}
                variant='outline'
                className='rounded-xl text-red-600 hover:bg-red-50 border-red-200'
              >
                <Trash2 className='w-4 h-4 mr-2' />
                Xóa
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className='max-w-7xl mx-auto p-4 sm:p-6'>
        <div className='grid lg:grid-cols-3 gap-6'>
          {/* Main Content - Left Side */}
          <div className='lg:col-span-2 space-y-6'>
            {/* Summary Card */}
            <div className='bg-white rounded-2xl shadow-sm p-6'>
              <h3 className='mb-4'>Tổng quan chuyến đi</h3>

              <div className='grid sm:grid-cols-2 gap-6 mb-6'>
                {/* Destination */}
                <div className='flex items-start gap-3'>
                  <div className='w-10 h-10 rounded-xl bg-[#0066FF]/10 flex items-center justify-center shrink-0'>
                    <MapPin className='w-5 h-5 text-[#0066FF]' />
                  </div>
                  <div>
                    <p className='text-sm text-muted-foreground mb-1'>
                      Điểm đến
                    </p>
                    <p>{payload.destination}</p>
                  </div>
                </div>

                {/* Budget */}
                <div className='flex items-start gap-3'>
                  <div className='w-10 h-10 rounded-xl bg-green-100 flex items-center justify-center shrink-0'>
                    <DollarSign className='w-5 h-5 text-green-700' />
                  </div>
                  <div>
                    <p className='text-sm text-muted-foreground mb-1'>
                      Ngân sách dự kiến
                    </p>
                    <p className='text-green-700'>
                      {payload.budget_min && payload.budget_max
                        ? `${(payload.budget_min / 1000000).toFixed(1)} - ${(payload.budget_max / 1000000).toFixed(1)} triệu VNĐ`
                        : payload.budget || 'Chưa xác định'}
                    </p>
                  </div>
                </div>

                {/* Duration */}
                <div className='flex items-start gap-3'>
                  <div className='w-10 h-10 rounded-xl bg-orange-100 flex items-center justify-center shrink-0'>
                    <Clock className='w-5 h-5 text-orange-700' />
                  </div>
                  <div>
                    <p className='text-sm text-muted-foreground mb-1'>
                      Thời gian
                    </p>
                    <p>{payload.duration}</p>
                  </div>
                </div>

                {/* Hotel */}
                {payload.hotel && (
                  <div className='flex items-start gap-3'>
                    <div className='w-10 h-10 rounded-xl bg-purple-100 flex items-center justify-center shrink-0'>
                      <Hotel className='w-5 h-5 text-purple-700' />
                    </div>
                    <div>
                      <p className='text-sm text-muted-foreground mb-1'>
                        Khách sạn
                      </p>
                      <p>{payload.hotel.name}</p>
                      {payload.hotel.price && (
                        <p className='text-sm text-muted-foreground'>
                          {payload.hotel.price}
                        </p>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Hotel Address */}
              {payload.hotel?.address && (
                <div className='mt-4 pt-4 border-t border-border'>
                  <div className='flex items-start gap-2 text-sm text-muted-foreground'>
                    <MapPin className='w-4 h-4 mt-0.5 shrink-0' />
                    <p>{payload.hotel.address}</p>
                  </div>
                </div>
              )}

              {/* Categorized Places */}
              {(categorizedPlaces.places?.length > 0 ||
                categorizedPlaces.food?.length > 0 ||
                categorizedPlaces.drink?.length > 0 ||
                categorizedPlaces.coffee?.length > 0) && (
                <div className='mt-6 pt-6 border-t border-border'>
                  <h4 className='mb-4'>Địa điểm trong lịch trình</h4>

                  {/* Places 🏛 */}
                  {categorizedPlaces.places &&
                    categorizedPlaces.places.length > 0 && (
                      <div className='mb-6'>
                        <h5 className='mb-3 flex items-center gap-2'>
                          <span className='text-xl'>🏛</span>
                          <span>Địa điểm tham quan</span>
                        </h5>
                        <div className='space-y-3'>
                          {categorizedPlaces.places.map((place, index) => (
                            <div
                              key={index}
                              className='bg-gray-50 rounded-lg p-4'
                            >
                              <p className='font-semibold mb-1'>{place.name}</p>
                              {place.description && (
                                <p className='text-sm text-muted-foreground'>
                                  {place.description}
                                </p>
                              )}
                              {place.address && (
                                <p className='text-xs text-muted-foreground mt-1'>
                                  {place.address}
                                </p>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                  {/* Food 🍽 */}
                  {categorizedPlaces.food &&
                    categorizedPlaces.food.length > 0 && (
                      <div className='mb-6'>
                        <h5 className='mb-3 flex items-center gap-2'>
                          <span className='text-xl'>🍽</span>
                          <span>Quán ăn</span>
                        </h5>
                        <div className='space-y-3'>
                          {categorizedPlaces.food.map((place, index) => (
                            <div
                              key={index}
                              className='bg-gray-50 rounded-lg p-4'
                            >
                              <p className='font-semibold mb-1'>{place.name}</p>
                              {place.description && (
                                <p className='text-sm text-muted-foreground'>
                                  {place.description}
                                </p>
                              )}
                              {place.address && (
                                <p className='text-xs text-muted-foreground mt-1'>
                                  {place.address}
                                </p>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                  {/* Drink 🥤 */}
                  {((categorizedPlaces.drink &&
                    categorizedPlaces.drink.length > 0) ||
                    (categorizedPlaces.coffee &&
                      categorizedPlaces.coffee.length > 0)) && (
                    <div className='mb-6'>
                      <h5 className='mb-3 flex items-center gap-2'>
                        <span className='text-xl'>🥤</span>
                        <span>Quán đồ uống</span>
                      </h5>
                      <div className='space-y-3'>
                        {(() => {
                          const drinkPlaces = categorizedPlaces.drink || [];
                          const coffeePlaces = categorizedPlaces.coffee || [];
                          const seen = new Set<string>();
                          const merged = [...drinkPlaces];
                          coffeePlaces.forEach((place) => {
                            if (!seen.has(place.name.toLowerCase())) {
                              seen.add(place.name.toLowerCase());
                              merged.push(place);
                            }
                          });
                          return merged;
                        })().map((place, index) => (
                          <div
                            key={index}
                            className='bg-gray-50 rounded-lg p-4'
                          >
                            <p className='font-semibold mb-1'>{place.name}</p>
                            {place.description && (
                              <p className='text-sm text-muted-foreground'>
                                {place.description}
                              </p>
                            )}
                            {place.address && (
                              <p className='text-xs text-muted-foreground mt-1'>
                                {place.address}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Daily Itinerary Timeline */}
            {payload.days &&
              payload.days.map((day) => (
                <div
                  key={day.day}
                  className='bg-white rounded-2xl shadow-sm p-6'
                >
                  {/* Day Header */}
                  <div className='flex items-center gap-4 mb-6'>
                    <div className='w-14 h-14 rounded-full bg-[#0066FF] text-white flex items-center justify-center shrink-0'>
                      <span className='font-semibold'>Ngày {day.day}</span>
                    </div>
                    <div>
                      <h3>Ngày {day.day}</h3>
                      <p className='text-muted-foreground'>{day.date}</p>
                    </div>
                  </div>

                  {/* Activities Timeline */}
                  <div className='ml-7 relative'>
                    {/* Timeline Line */}
                    <div className='absolute left-0 top-0 bottom-0 w-0.5 bg-gradient-to-b from-[#0066FF]/30 via-[#0066FF]/20 to-transparent' />

                    {/* Activities */}
                    <div className='space-y-6'>
                      {day.activities.map((activity, index) => {
                        const category =
                          activity.icon || activity.category || 'culture';

                        // Track previous activity's end time for calculation
                        let previousEndTime: string | null = null;
                        if (index > 0) {
                          const previousActivity = day.activities[index - 1];
                          const prevTimeRange = parseTimeRange(
                            previousActivity.time,
                            previousActivity.duration,
                            null,
                            '09:00',
                          );
                          previousEndTime = prevTimeRange?.endTime || null;

                          // Add travel time if available
                          if (previousEndTime && activity.travelTime) {
                            const travelMinutes = extractMinutes(
                              activity.travelTime,
                            );
                            const timeMatch =
                              previousEndTime.match(/(\d{1,2}):(\d{2})/);
                            if (timeMatch) {
                              let hour = parseInt(timeMatch[1]);
                              let min = parseInt(timeMatch[2]) + travelMinutes;
                              while (min >= 60) {
                                hour += 1;
                                min -= 60;
                              }
                              if (hour >= 24) {
                                hour = 23;
                                min = 59;
                              }
                              previousEndTime = `${hour.toString().padStart(2, '0')}:${min.toString().padStart(2, '0')}`;
                            }
                          }
                        }

                        // Parse time range (always try to show time range)
                        const timeRange = parseTimeRange(
                          activity.time,
                          activity.duration,
                          previousEndTime,
                          index === 0 ? '09:00' : previousEndTime || '09:00',
                        );

                        // Always use calculated duration from time range to ensure they match
                        // If time range exists, use its calculated duration
                        // Otherwise, try to calculate from provided duration
                        let durationToDisplay: number | null = null;
                        if (timeRange) {
                          durationToDisplay =
                            timeRange.calculatedDurationMinutes;
                        } else if (activity.duration) {
                          durationToDisplay = extractMinutes(activity.duration);
                        }

                        // Format duration - always use calculated duration to match time range
                        const formattedDuration =
                          durationToDisplay !== null && durationToDisplay > 0
                            ? formatDuration(`${durationToDisplay} phút`)
                            : null;

                        // Ensure we always show both if we have at least one
                        const shouldShowTimeInfo =
                          timeRange || formattedDuration;

                        return (
                          <div
                            key={activity.id || `act-${day.day}-${index}`}
                            className='relative pl-8'
                          >
                            {/* Timeline Dot */}
                            <div className='absolute left-[-4px] top-6 w-2.5 h-2.5 rounded-full bg-[#0066FF] ring-4 ring-white' />

                            {/* Travel Time Badge - Show between activities */}
                            {/* Show travelTimeToNext from previous activity, or travelTime if it's the first activity */}
                            {(() => {
                              // Use travelTimeToNext from previous activity if available, otherwise use travelTime for first activity
                              const previousActivity =
                                index > 0 ? day.activities[index - 1] : null;
                              const travelTimeToDisplay =
                                previousActivity?.travelTimeToNext ||
                                (index === 0 ? activity.travelTime : null);

                              if (!travelTimeToDisplay) return null;

                              // Determine transport mode icon based on travel time string or default to driving
                              const travelTimeLower =
                                travelTimeToDisplay.toLowerCase();
                              let transportIcon = '🚗'; // Default to car
                              let transportText = 'xe';

                              if (
                                travelTimeLower.includes('xe máy') ||
                                travelTimeLower.includes('máy') ||
                                travelTimeLower.includes('motorbike')
                              ) {
                                transportIcon = '🏍️';
                                transportText = 'xe máy';
                              } else if (
                                travelTimeLower.includes('bộ') ||
                                travelTimeLower.includes('đi bộ') ||
                                travelTimeLower.includes('walking')
                              ) {
                                transportIcon = '🚶';
                                transportText = 'đi bộ';
                              } else if (
                                travelTimeLower.includes('taxi') ||
                                travelTimeLower.includes('xe') ||
                                travelTimeLower.includes('car') ||
                                travelTimeLower.includes('driving')
                              ) {
                                transportIcon = '🚗';
                                transportText = 'xe';
                              }

                              return (
                                <div className='mb-3 flex items-center justify-center'>
                                  <div className='flex items-center gap-2 text-sm bg-[#0066FF]/5 text-[#0066FF] px-3 py-1.5 rounded-lg border border-[#0066FF]/10'>
                                    <Navigation className='w-3.5 h-3.5' />
                                    <span>{travelTimeToDisplay}</span>
                                    <span>•</span>
                                    <span>
                                      {transportIcon} {transportText}
                                    </span>
                                  </div>
                                </div>
                              );
                            })()}

                            {/* Activity Card */}
                            <div className='bg-gray-50 rounded-xl p-5 hover:shadow-md transition-shadow border border-gray-100'>
                              <div className='flex items-start gap-4 mb-4'>
                                {/* Category Icon */}
                                <div
                                  className={`w-12 h-12 rounded-xl ${getCategoryColor(category)} flex items-center justify-center shrink-0`}
                                >
                                  {(() => {
                                    const Icon = getCategoryIcon(category);
                                    return <Icon className='w-6 h-6' />;
                                  })()}
                                </div>

                                {/* Activity Info */}
                                <div className='flex-1 min-w-0'>
                                  <h4 className='mb-1 font-semibold'>
                                    {activity.name}
                                  </h4>

                                  {/* Address */}
                                  {activity.address && (
                                    <div className='flex items-start gap-1.5 text-sm text-muted-foreground mb-3'>
                                      <MapPin className='w-3.5 h-3.5 mt-0.5 shrink-0' />
                                      <p>{activity.address}</p>
                                    </div>
                                  )}

                                  {/* Time Range and Duration Row - Horizontal, time range left, duration right */}
                                  {shouldShowTimeInfo && (
                                    <div className='flex items-center justify-between mb-3'>
                                      {/* Time Range - Left side */}
                                      {timeRange && (
                                        <div className='flex items-center gap-2 text-sm'>
                                          <Clock className='w-4 h-4 text-[#0066FF] shrink-0' />
                                          <span className='text-muted-foreground'>
                                            {timeRange.startTime} –{' '}
                                            {timeRange.endTime}
                                          </span>
                                        </div>
                                      )}

                                      {/* Duration - Right side */}
                                      {(formattedDuration || timeRange) && (
                                        <div className='flex items-center gap-2 text-sm'>
                                          <Clock className='w-4 h-4 text-orange-500 shrink-0' />
                                          <span className='text-muted-foreground'>
                                            Dự kiến{' '}
                                            {formattedDuration ||
                                              (timeRange
                                                ? formatDuration(
                                                    `${timeRange.calculatedDurationMinutes} phút`,
                                                  )
                                                : '')}
                                          </span>
                                        </div>
                                      )}
                                    </div>
                                  )}

                                  {/* Rating - Below time range (vertical) */}
                                  {activity.rating && (
                                    <div className='flex items-center gap-2 text-sm mb-3'>
                                      <Star className='w-4 h-4 fill-yellow-400 text-yellow-400' />
                                      <span className='text-muted-foreground'>
                                        {activity.rating}/5
                                      </span>
                                    </div>
                                  )}
                                </div>
                              </div>

                              {/* Cost - Below rating */}
                              {activity.cost && (
                                <div className='flex items-center gap-2 text-sm mb-4'>
                                  <DollarSign className='w-4 h-4 text-green-600' />
                                  <span className='text-green-700'>
                                    {activity.cost === 'Miễn phí' ||
                                    activity.cost === '0'
                                      ? 'Miễn phí'
                                      : activity.cost}
                                  </span>
                                </div>
                              )}

                              {/* Notes */}
                              {activity.notes && (
                                <div className='bg-white rounded-lg p-3 border border-border'>
                                  <p className='text-sm text-muted-foreground'>
                                    💡{' '}
                                    <span className='font-medium'>Gợi ý:</span>{' '}
                                    {activity.notes}
                                  </p>
                                </div>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              ))}
          </div>

          {/* Sidebar - Right Side */}
          <div className='space-y-6'>
            {/* Map Preview */}
            <div className='bg-white rounded-2xl shadow-sm p-6 sticky top-24'>
              <h3 className='mb-4 flex items-center gap-2'>
                <MapPin className='w-5 h-5 text-[#0066FF]' />
                Bản đồ lịch trình
              </h3>

              {/* Map Placeholder */}
              <div className='aspect-square bg-gradient-to-br from-[#0066FF]/10 to-[#00C29A]/10 rounded-xl flex items-center justify-center mb-4'>
                <div className='text-center'>
                  <MapPin className='w-12 h-12 text-[#0066FF] mx-auto mb-2' />
                  <p className='text-sm text-muted-foreground'>
                    Xem bản đồ tương tác
                  </p>
                </div>
              </div>

              <Button className='w-full rounded-xl bg-[#0066FF] hover:bg-[#0052CC]'>
                <MapPin className='w-4 h-4 mr-2' />
                Mở bản đồ đầy đủ
              </Button>

              {/* Quick Stats */}
              <div className='mt-6 pt-6 border-t border-border space-y-3'>
                <div className='flex items-center justify-between text-sm'>
                  <span className='text-muted-foreground'>Tổng điểm đến</span>
                  <span className='font-medium'>
                    {payload.days?.reduce(
                      (acc, day) => acc + (day.activities?.length || 0),
                      0,
                    ) || 0}{' '}
                    địa điểm
                  </span>
                </div>
                {payload.days && (
                  <div className='flex items-center justify-between text-sm'>
                    <span className='text-muted-foreground'>Số ngày</span>
                    <span className='font-medium'>{totalDays} ngày</span>
                  </div>
                )}
              </div>
            </div>

            {/* Budget Info */}
            <div className='bg-white rounded-2xl shadow-sm p-6'>
              <h3 className='mb-4 flex items-center gap-2'>
                <DollarSign className='w-5 h-5 text-green-600' />
                Ngân sách
              </h3>

              <div className='space-y-3'>
                {payload.budget_min && payload.budget_max ? (
                  <>
                    <div className='flex items-center justify-between pb-3 border-b border-border'>
                      <span className='text-sm text-muted-foreground'>
                        Ngân sách tối thiểu
                      </span>
                      <span className='font-medium'>
                        {(payload.budget_min / 1000000).toFixed(1)} triệu VNĐ
                      </span>
                    </div>
                    <div className='flex items-center justify-between pb-3 border-b border-border'>
                      <span className='text-sm text-muted-foreground'>
                        Ngân sách tối đa
                      </span>
                      <span className='font-medium'>
                        {(payload.budget_max / 1000000).toFixed(1)} triệu VNĐ
                      </span>
                    </div>
                  </>
                ) : (
                  <div className='pb-3 border-b border-border'>
                    <span className='text-sm text-muted-foreground'>
                      {payload.budget || 'Chưa xác định'}
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
