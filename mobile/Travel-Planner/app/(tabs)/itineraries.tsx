import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
  Alert,
  Modal,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { MapPin, Calendar, DollarSign, X, Trash2 } from 'lucide-react-native';
import { API_ENDPOINTS, getAuthHeaders } from '@/config/api';
import { Button } from '@/components/ui/button';
import { useTheme } from '@/contexts/ThemeContext';

interface Itinerary {
  id: number;
  title: string;
  payload: {
    destination: string;
    duration: string;
    budget: string;
    days?: any[];
    hotel?: any;
  };
  created_at: string;
}

export default function ItinerariesScreen() {
  const { colors } = useTheme();
  const [itineraries, setItineraries] = useState<Itinerary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedItinerary, setSelectedItinerary] = useState<Itinerary | null>(
    null,
  );
  const [showDetailModal, setShowDetailModal] = useState(false);

  useEffect(() => {
    loadItineraries();
  }, []);

  const loadItineraries = async () => {
    try {
      const headers = await getAuthHeaders();

      const response = await fetch(API_ENDPOINTS.ITINERARIES.LIST, {
        headers,
      });

      if (response.ok) {
        const data = await response.json();

        setItineraries(data.items || []);
      } else {
        const errorText = await response.text();
        console.error('❌ [Itineraries] Error response:', errorText);
      }
    } catch (error) {
      console.error('❌ [Itineraries] Error loading itineraries:', error);
    } finally {
      setIsLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = () => {
    setRefreshing(true);
    loadItineraries();
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('vi-VN', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
  };

  const handleViewDetail = async (itinerary: Itinerary) => {
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(
        API_ENDPOINTS.ITINERARIES.GET(itinerary.id),
        {
          headers,
        },
      );

      if (response.ok) {
        const data = await response.json();
        setSelectedItinerary(data);
        setShowDetailModal(true);
      }
    } catch (error) {
      console.error('Error loading itinerary detail:', error);
      Alert.alert('Lỗi', 'Không thể tải chi tiết lịch trình');
    }
  };

  const handleDelete = (itinerary: Itinerary) => {
    Alert.alert('Xóa lịch trình', 'Bạn có chắc chắn muốn xóa lịch trình này?', [
      { text: 'Hủy', style: 'cancel' },
      {
        text: 'Xóa',
        style: 'destructive',
        onPress: async () => {
          try {
            const headers = await getAuthHeaders();
            const response = await fetch(
              `${API_ENDPOINTS.ITINERARIES.LIST}/${itinerary.id}`,
              {
                method: 'DELETE',
                headers,
              },
            );

            if (response.ok) {
              setItineraries((prev) =>
                prev.filter((item) => item.id !== itinerary.id),
              );
              Alert.alert('Thành công', 'Đã xóa lịch trình');
            } else {
              throw new Error('Không thể xóa');
            }
          } catch (error) {
            console.error('Error deleting itinerary:', error);
            Alert.alert('Lỗi', 'Không thể xóa lịch trình');
          }
        },
      },
    ]);
  };

  if (isLoading) {
    return (
      <SafeAreaView
        className='flex-1'
        edges={['top']}
        style={{ backgroundColor: colors.background }}
      >
        <View
          className='px-4 py-4 border-b'
          style={{ backgroundColor: colors.card, borderColor: colors.border }}
        >
          <Text
            className='text-2xl font-bold'
            style={{ color: colors.foreground }}
          >
            Lịch trình đã lưu
          </Text>
        </View>
        <View className='flex-1 items-center justify-center'>
          <ActivityIndicator size='large' color={colors.primary} />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView
      className='flex-1'
      edges={['top']}
      style={{ backgroundColor: colors.background }}
    >
      <View
        className='px-4 py-4 border-b'
        style={{ backgroundColor: colors.card, borderColor: colors.border }}
      >
        <Text
          className='text-2xl font-bold'
          style={{ color: colors.foreground }}
        >
          Lịch trình đã lưu
        </Text>
      </View>

      <ScrollView
        className='flex-1'
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      >
        {itineraries.length === 0 ? (
          <View className='flex-1 items-center justify-center py-24'>
            <Text className='text-6xl mb-4'>📋</Text>
            <Text
              className='text-lg font-semibold mb-2'
              style={{ color: colors.foreground }}
            >
              Chưa có lịch trình nào
            </Text>
            <Text
              className='text-sm text-center'
              style={{ color: colors.mutedForeground }}
            >
              Lưu lịch trình từ cuộc trò chuyện để xem ở đây
            </Text>
          </View>
        ) : (
          <View className='p-4'>
            {itineraries.map((itinerary, index) => {
              return (
                <View
                  key={itinerary.id}
                  className='rounded-2xl border p-4 mb-4'
                  style={{
                    backgroundColor: colors.card,
                    borderColor: colors.border,
                  }}
                >
                  <TouchableOpacity
                    onPress={() => handleViewDetail(itinerary)}
                    activeOpacity={0.7}
                  >
                    <Text
                      className='text-lg font-bold mb-3'
                      style={{ color: colors.foreground }}
                    >
                      {itinerary.title}
                    </Text>

                    <View className='flex-row items-center mb-2'>
                      <View
                        className='w-8 h-8 rounded-full items-center justify-center mr-3'
                        style={{ backgroundColor: colors.accent }}
                      >
                        <MapPin size={16} color={colors.primary} />
                      </View>
                      <Text
                        className='text-sm'
                        style={{ color: colors.mutedForeground }}
                      >
                        {itinerary.payload.destination}
                      </Text>
                    </View>

                    <View className='flex-row items-center mb-2'>
                      <View
                        className='w-8 h-8 rounded-full items-center justify-center mr-3'
                        style={{ backgroundColor: colors.accent }}
                      >
                        <Calendar size={16} color={colors.primary} />
                      </View>
                      <Text
                        className='text-sm'
                        style={{ color: colors.mutedForeground }}
                      >
                        {itinerary.payload.duration}
                      </Text>
                    </View>

                    <View className='flex-row items-center mb-3'>
                      <View
                        className='w-8 h-8 rounded-full items-center justify-center mr-3'
                        style={{ backgroundColor: colors.accent }}
                      >
                        <DollarSign size={16} color={colors.primary} />
                      </View>
                      <Text
                        className='text-sm'
                        style={{ color: colors.mutedForeground }}
                      >
                        {itinerary.payload.budget}
                      </Text>
                    </View>

                    <View
                      className='pt-3 border-t'
                      style={{ borderColor: colors.border }}
                    >
                      <Text
                        className='text-xs'
                        style={{ color: colors.mutedForeground }}
                      >
                        Đã lưu: {formatDate(itinerary.created_at)}
                      </Text>
                    </View>
                  </TouchableOpacity>

                  <TouchableOpacity
                    onPress={() => handleDelete(itinerary)}
                    className='absolute top-4 right-4 w-8 h-8 rounded-full items-center justify-center'
                    style={{ backgroundColor: `${colors.destructive}20` }}
                  >
                    <Trash2 size={16} color={colors.destructive} />
                  </TouchableOpacity>
                </View>
              );
            })}
          </View>
        )}
      </ScrollView>

      <Modal
        visible={showDetailModal}
        animationType='slide'
        presentationStyle='pageSheet'
        onRequestClose={() => setShowDetailModal(false)}
      >
        <SafeAreaView
          className='flex-1'
          edges={['top']}
          style={{ backgroundColor: colors.background }}
        >
          <View
            className='flex-row items-center justify-between px-4 py-4 border-b'
            style={{ backgroundColor: colors.card, borderColor: colors.border }}
          >
            <Text
              className='text-xl font-bold'
              style={{ color: colors.foreground }}
            >
              Chi tiết lịch trình
            </Text>
            <TouchableOpacity onPress={() => setShowDetailModal(false)}>
              <X size={24} color={colors.mutedForeground} />
            </TouchableOpacity>
          </View>

          <ScrollView className='flex-1'>
            {selectedItinerary && (
              <View className='p-4'>
                <View
                  className='rounded-2xl border p-4 mb-4'
                  style={{
                    backgroundColor: colors.card,
                    borderColor: colors.border,
                  }}
                >
                  <Text
                    className='text-2xl font-bold mb-4'
                    style={{ color: colors.foreground }}
                  >
                    {selectedItinerary.title}
                  </Text>

                  <View className='flex-row items-center mb-3'>
                    <MapPin size={20} color={colors.primary} />
                    <Text
                      className='text-base font-semibold ml-3'
                      style={{ color: colors.foreground }}
                    >
                      {selectedItinerary.payload.destination}
                    </Text>
                  </View>

                  <View className='flex-row items-center mb-3'>
                    <Calendar size={20} color={colors.primary} />
                    <Text
                      className='text-base ml-3'
                      style={{ color: colors.mutedForeground }}
                    >
                      {selectedItinerary.payload.duration}
                    </Text>
                  </View>

                  <View className='flex-row items-center'>
                    <DollarSign size={20} color={colors.primary} />
                    <Text
                      className='text-base ml-3'
                      style={{ color: colors.mutedForeground }}
                    >
                      {selectedItinerary.payload.budget}
                    </Text>
                  </View>
                </View>

                {selectedItinerary.payload.days &&
                  selectedItinerary.payload.days.length > 0 && (
                    <View>
                      <Text
                        className='text-lg font-bold mb-3'
                        style={{ color: colors.foreground }}
                      >
                        Lịch trình chi tiết
                      </Text>
                      {selectedItinerary.payload.days.map(
                        (day: any, index: number) => (
                          <View
                            key={index}
                            className='rounded-2xl border p-4 mb-4'
                            style={{
                              backgroundColor: colors.card,
                              borderColor: colors.border,
                            }}
                          >
                            <Text
                              className='text-base font-bold mb-3'
                              style={{ color: colors.foreground }}
                            >
                              Ngày {day.day} - {day.date}
                            </Text>
                            {day.activities &&
                              day.activities.map(
                                (activity: any, actIndex: number) => (
                                  <View
                                    key={actIndex}
                                    className='mb-3 pb-3 border-b last:border-b-0'
                                    style={{ borderColor: colors.border }}
                                  >
                                    <Text
                                      className='text-sm font-semibold'
                                      style={{ color: colors.foreground }}
                                    >
                                      {activity.name}
                                    </Text>
                                    {activity.time && (
                                      <Text
                                        className='text-xs mt-1'
                                        style={{
                                          color: colors.mutedForeground,
                                        }}
                                      >
                                        ⏰ {activity.time}
                                      </Text>
                                    )}
                                    {activity.address && (
                                      <Text
                                        className='text-xs mt-1'
                                        style={{
                                          color: colors.mutedForeground,
                                        }}
                                      >
                                        📍 {activity.address}
                                      </Text>
                                    )}
                                  </View>
                                ),
                              )}
                          </View>
                        ),
                      )}
                    </View>
                  )}
              </View>
            )}
          </ScrollView>

          <View
            className='p-4 border-t'
            style={{ backgroundColor: colors.card, borderColor: colors.border }}
          >
            <Button onPress={() => setShowDetailModal(false)}>Đóng</Button>
          </View>
        </SafeAreaView>
      </Modal>
    </SafeAreaView>
  );
}
