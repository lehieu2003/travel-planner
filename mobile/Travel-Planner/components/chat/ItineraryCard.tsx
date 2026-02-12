import React, { useState } from 'react';
import { View, Text, TouchableOpacity } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import {
  MapPin,
  Clock,
  Star,
  Utensils,
  Mountain,
  Coffee,
  DollarSign,
  Navigation,
  ChevronDown,
  ChevronUp,
  Hotel,
} from 'lucide-react-native';

export interface Activity {
  id: string;
  name: string;
  icon: string;
  time: string;
  duration: string;
  rating?: number | null;
  address?: string | null;
  cost?: string | null;
  travelTime?: string | null;
}

export interface DayItinerary {
  day: number;
  date: string;
  activities: Activity[];
}

export interface HotelInfo {
  name: string;
  price: string;
  rating?: number | null;
  image?: string;
}

export interface ItineraryData {
  destination: string;
  duration: string;
  budget: string;
  days: DayItinerary[];
  hotel?: HotelInfo;
}

interface ItineraryCardProps {
  itineraryData: ItineraryData;
}

const getActivityIcon = (icon: string) => {
  const iconProps = { size: 20, color: '#00C29A' };
  switch (icon) {
    case 'food':
      return <Utensils {...iconProps} />;
    case 'nature':
    case 'natural':
    case 'attraction':
      return <Mountain {...iconProps} />;
    case 'coffee':
    case 'drink':
      return <Coffee {...iconProps} />;
    case 'park':
    case 'culture':
      return <MapPin {...iconProps} />;
    case 'hotel':
      return <Hotel {...iconProps} />;
    default:
      return <MapPin {...iconProps} />;
  }
};

export function ItineraryCard({ itineraryData }: ItineraryCardProps) {
  const [expandedDays, setExpandedDays] = useState<Set<number>>(
    new Set([1]), // First day expanded by default
  );

  const toggleDay = (day: number) => {
    const newExpanded = new Set(expandedDays);
    if (newExpanded.has(day)) {
      newExpanded.delete(day);
    } else {
      newExpanded.add(day);
    }
    setExpandedDays(newExpanded);
  };

  if (!itineraryData) {
    return null;
  }

  return (
    <View className='bg-white rounded-2xl border border-slate-200 p-4 mb-4'>
      {/* Trip Summary */}
      <LinearGradient
        colors={['#EFF6FF', '#ECFDF5']}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        className='rounded-xl p-4 mb-4'
      >
        <Text className='text-lg font-bold text-slate-900 mb-3'>
          {itineraryData.destination}
        </Text>

        {/* Duration and Budget */}
        <View className='flex-row gap-2'>
          {/* Duration Card */}
          <View className='flex-1 bg-white rounded-lg p-3 border border-slate-200'>
            <View className='flex-row items-center gap-2 mb-1'>
              <View className='w-8 h-8 rounded-lg bg-blue-50 items-center justify-center'>
                <Clock size={16} color='#0066FF' />
              </View>
              <Text className='text-xs text-slate-600'>Thời lượng</Text>
            </View>
            <Text className='text-sm font-semibold text-slate-900'>
              {itineraryData.duration}
            </Text>
          </View>

          {/* Budget Card */}
          <View className='flex-1 bg-white rounded-lg p-3 border border-slate-200'>
            <View className='flex-row items-center gap-2 mb-1'>
              <View className='w-8 h-8 rounded-lg bg-amber-50 items-center justify-center'>
                <DollarSign size={16} color='#F59E0B' />
              </View>
              <Text className='text-xs text-slate-600'>Ngân sách</Text>
            </View>
            <Text className='text-sm font-semibold text-slate-900'>
              {itineraryData.budget}
            </Text>
          </View>
        </View>
      </LinearGradient>

      {/* Days */}
      <View className='space-y-3'>
        {itineraryData.days.map((day) => (
          <View key={day.day}>
            {/* Day Header */}
            <TouchableOpacity
              onPress={() => toggleDay(day.day)}
              className='flex-row items-center gap-3 mb-2'
              activeOpacity={0.7}
            >
              <View className='w-10 h-10 rounded-full bg-blue-600 items-center justify-center'>
                <Text className='text-white font-bold'>{day.day}</Text>
              </View>
              <View className='flex-1'>
                <Text className='text-base font-semibold text-slate-900'>
                  Ngày {day.day}
                </Text>
                <Text className='text-sm text-slate-600'>{day.date}</Text>
              </View>
              {expandedDays.has(day.day) ? (
                <ChevronUp size={20} color='#64748B' />
              ) : (
                <ChevronDown size={20} color='#64748B' />
              )}
            </TouchableOpacity>

            {/* Activities */}
            {expandedDays.has(day.day) && (
              <View className='ml-5 border-l-2 border-blue-200 pl-4 space-y-3'>
                {day.activities.length === 0 ? (
                  <View className='bg-slate-50 rounded-xl border border-dashed border-slate-300 p-4'>
                    <Text className='text-sm text-slate-600 text-center'>
                      Chưa có hoạt động được lên kế hoạch
                    </Text>
                  </View>
                ) : (
                  day.activities.map((activity) => (
                    <View
                      key={activity.id}
                      className='bg-white rounded-xl border border-slate-200 p-3'
                    >
                      <View className='flex-row items-start gap-3'>
                        <View className='w-10 h-10 rounded-xl bg-emerald-50 items-center justify-center'>
                          {getActivityIcon(activity.icon)}
                        </View>
                        <View className='flex-1'>
                          <Text className='text-sm font-semibold text-slate-900 mb-2'>
                            {activity.name}
                          </Text>

                          {/* Address */}
                          {activity.address && (
                            <View className='flex-row items-start gap-1.5 mb-2'>
                              <MapPin size={14} color='#64748B' />
                              <Text
                                className='flex-1 text-xs text-slate-600'
                                numberOfLines={2}
                              >
                                {activity.address}
                              </Text>
                            </View>
                          )}

                          {/* Details */}
                          <View className='flex-row flex-wrap items-center gap-2'>
                            <View className='flex-row items-center gap-1'>
                              <Clock size={12} color='#64748B' />
                              <Text className='text-xs text-slate-600'>
                                {activity.time}
                              </Text>
                            </View>
                            <Text className='text-xs text-slate-400'>•</Text>
                            <Text className='text-xs text-slate-600'>
                              {activity.duration}
                            </Text>
                            {activity.travelTime && (
                              <>
                                <Text className='text-xs text-slate-400'>
                                  •
                                </Text>
                                <View className='flex-row items-center gap-1'>
                                  <Navigation size={12} color='#64748B' />
                                  <Text className='text-xs text-slate-600'>
                                    {activity.travelTime}
                                  </Text>
                                </View>
                              </>
                            )}
                            {activity.rating && (
                              <>
                                <Text className='text-xs text-slate-400'>
                                  •
                                </Text>
                                <View className='flex-row items-center gap-1'>
                                  <Star
                                    size={12}
                                    color='#FBBF24'
                                    fill='#FBBF24'
                                  />
                                  <Text className='text-xs text-slate-600'>
                                    {activity.rating.toFixed(1)}
                                  </Text>
                                </View>
                              </>
                            )}
                          </View>
                        </View>
                      </View>
                    </View>
                  ))
                )}
              </View>
            )}
          </View>
        ))}
      </View>

      {/* Hotel Recommendation */}
      {itineraryData.hotel && (
        <View className='mt-4 pt-4 border-t border-slate-200'>
          <Text className='text-base font-semibold text-slate-900 mb-3'>
            🏨 Khách sạn gợi ý
          </Text>
          <View className='bg-white rounded-xl border border-slate-200 overflow-hidden'>
            <View className='p-3'>
              <View className='flex-row items-start justify-between mb-2'>
                <Text className='flex-1 text-sm font-semibold text-slate-900'>
                  {itineraryData.hotel.name}
                </Text>
                {itineraryData.hotel.rating && (
                  <View className='flex-row items-center gap-1 ml-2 bg-slate-100 px-2 py-1 rounded-full'>
                    <Star size={12} color='#FBBF24' fill='#FBBF24' />
                    <Text className='text-xs font-medium text-slate-900'>
                      {itineraryData.hotel.rating}
                    </Text>
                  </View>
                )}
              </View>
              <Text className='text-sm text-blue-600 font-semibold'>
                {itineraryData.hotel.price}{' '}
                {itineraryData.hotel.price.includes('VNĐ') ? '' : 'VNĐ'}
              </Text>
            </View>
          </View>
        </View>
      )}
    </View>
  );
}
