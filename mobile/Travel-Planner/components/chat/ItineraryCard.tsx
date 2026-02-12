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
import { useTheme } from '@/contexts/ThemeContext';

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
  const { colors, activeTheme } = useTheme();
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
    <View
      className='rounded-2xl border p-4 mb-4'
      style={{ backgroundColor: colors.card, borderColor: colors.border }}
    >
      {/* Trip Summary */}
      <LinearGradient
        colors={
          activeTheme === 'dark'
            ? ['#1e293b', '#0f172a']
            : ['#EFF6FF', '#ECFDF5']
        }
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        className='rounded-xl p-4 mb-4'
      >
        <Text
          className='text-lg font-bold mb-3'
          style={{ color: colors.foreground }}
        >
          {itineraryData.destination}
        </Text>

        {/* Duration and Budget */}
        <View className='flex-row gap-2'>
          {/* Duration Card */}
          <View
            className='flex-1 rounded-lg p-3 border'
            style={{
              backgroundColor: colors.background,
              borderColor: colors.border,
            }}
          >
            <View className='flex-row items-center gap-2 mb-1'>
              <View
                className='w-8 h-8 rounded-lg items-center justify-center'
                style={{ backgroundColor: colors.accent }}
              >
                <Clock size={16} color={colors.primary} />
              </View>
              <Text
                className='text-xs'
                style={{ color: colors.mutedForeground }}
              >
                Thời lượng
              </Text>
            </View>
            <Text
              className='text-sm font-semibold'
              style={{ color: colors.foreground }}
            >
              {itineraryData.duration}
            </Text>
          </View>

          {/* Budget Card */}
          <View
            className='flex-1 rounded-lg p-3 border'
            style={{
              backgroundColor: colors.background,
              borderColor: colors.border,
            }}
          >
            <View className='flex-row items-center gap-2 mb-1'>
              <View
                className='w-8 h-8 rounded-lg items-center justify-center'
                style={{ backgroundColor: colors.accent }}
              >
                <DollarSign size={16} color='#F59E0B' />
              </View>
              <Text
                className='text-xs'
                style={{ color: colors.mutedForeground }}
              >
                Ngân sách
              </Text>
            </View>
            <Text
              className='text-sm font-semibold'
              style={{ color: colors.foreground }}
            >
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
              <View
                className='w-10 h-10 rounded-full items-center justify-center'
                style={{ backgroundColor: colors.primary }}
              >
                <Text className='text-white font-bold'>{day.day}</Text>
              </View>
              <View className='flex-1'>
                <Text
                  className='text-base font-semibold'
                  style={{ color: colors.foreground }}
                >
                  Ngày {day.day}
                </Text>
                <Text
                  className='text-sm'
                  style={{ color: colors.mutedForeground }}
                >
                  {day.date}
                </Text>
              </View>
              {expandedDays.has(day.day) ? (
                <ChevronUp size={20} color={colors.mutedForeground} />
              ) : (
                <ChevronDown size={20} color={colors.mutedForeground} />
              )}
            </TouchableOpacity>

            {/* Activities */}
            {expandedDays.has(day.day) && (
              <View
                className='ml-5 border-l-2 pl-4 space-y-3'
                style={{
                  borderColor:
                    activeTheme === 'dark' ? colors.border : '#BFDBFE',
                }}
              >
                {day.activities.length === 0 ? (
                  <View
                    className='rounded-xl border border-dashed p-4'
                    style={{
                      backgroundColor: colors.muted,
                      borderColor: colors.border,
                    }}
                  >
                    <Text
                      className='text-sm text-center'
                      style={{ color: colors.mutedForeground }}
                    >
                      Chưa có hoạt động được lên kế hoạch
                    </Text>
                  </View>
                ) : (
                  day.activities.map((activity) => (
                    <View
                      key={activity.id}
                      className='rounded-xl border p-3'
                      style={{
                        backgroundColor: colors.card,
                        borderColor: colors.border,
                      }}
                    >
                      <View className='flex-row items-start gap-3'>
                        <View
                          className='w-10 h-10 rounded-xl items-center justify-center'
                          style={{
                            backgroundColor:
                              activeTheme === 'dark'
                                ? colors.accent
                                : '#D1FAE5',
                          }}
                        >
                          {getActivityIcon(activity.icon)}
                        </View>
                        <View className='flex-1'>
                          <Text
                            className='text-sm font-semibold mb-2'
                            style={{ color: colors.foreground }}
                          >
                            {activity.name}
                          </Text>

                          {/* Address */}
                          {activity.address && (
                            <View className='flex-row items-start gap-1.5 mb-2'>
                              <MapPin
                                size={14}
                                color={colors.mutedForeground}
                              />
                              <Text
                                className='flex-1 text-xs'
                                numberOfLines={2}
                                style={{ color: colors.mutedForeground }}
                              >
                                {activity.address}
                              </Text>
                            </View>
                          )}

                          {/* Details */}
                          <View className='flex-row flex-wrap items-center gap-2'>
                            <View className='flex-row items-center gap-1'>
                              <Clock size={12} color={colors.mutedForeground} />
                              <Text
                                className='text-xs'
                                style={{ color: colors.mutedForeground }}
                              >
                                {activity.time}
                              </Text>
                            </View>
                            <Text
                              className='text-xs'
                              style={{ color: colors.border }}
                            >
                              •
                            </Text>
                            <Text
                              className='text-xs'
                              style={{ color: colors.mutedForeground }}
                            >
                              {activity.duration}
                            </Text>
                            {activity.travelTime && (
                              <>
                                <Text
                                  className='text-xs'
                                  style={{ color: colors.border }}
                                >
                                  •
                                </Text>
                                <View className='flex-row items-center gap-1'>
                                  <Navigation
                                    size={12}
                                    color={colors.mutedForeground}
                                  />
                                  <Text
                                    className='text-xs'
                                    style={{ color: colors.mutedForeground }}
                                  >
                                    {activity.travelTime}
                                  </Text>
                                </View>
                              </>
                            )}
                            {activity.rating && (
                              <>
                                <Text
                                  className='text-xs'
                                  style={{ color: colors.border }}
                                >
                                  •
                                </Text>
                                <View className='flex-row items-center gap-1'>
                                  <Star
                                    size={12}
                                    color='#FBBF24'
                                    fill='#FBBF24'
                                  />
                                  <Text
                                    className='text-xs'
                                    style={{ color: colors.mutedForeground }}
                                  >
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
        <View
          className='mt-4 pt-4 border-t'
          style={{ borderColor: colors.border }}
        >
          <Text
            className='text-base font-semibold mb-3'
            style={{ color: colors.foreground }}
          >
            🏨 Khách sạn gợi ý
          </Text>
          <View
            className='rounded-xl border overflow-hidden'
            style={{ backgroundColor: colors.card, borderColor: colors.border }}
          >
            <View className='p-3'>
              <View className='flex-row items-start justify-between mb-2'>
                <Text
                  className='flex-1 text-sm font-semibold'
                  style={{ color: colors.foreground }}
                >
                  {itineraryData.hotel.name}
                </Text>
                {itineraryData.hotel.rating && (
                  <View
                    className='flex-row items-center gap-1 ml-2 px-2 py-1 rounded-full'
                    style={{ backgroundColor: colors.muted }}
                  >
                    <Star size={12} color='#FBBF24' fill='#FBBF24' />
                    <Text
                      className='text-xs font-medium'
                      style={{ color: colors.foreground }}
                    >
                      {itineraryData.hotel.rating}
                    </Text>
                  </View>
                )}
              </View>
              <Text
                className='text-sm font-semibold'
                style={{ color: colors.primary }}
              >
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
