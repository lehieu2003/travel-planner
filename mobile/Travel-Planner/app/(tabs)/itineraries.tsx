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
      }
    } catch (error) {
      console.error('Error loading itineraries:', error);
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
      <SafeAreaView className='flex-1 bg-slate-50' edges={['top']}>
        <View className='px-4 py-4 bg-white border-b border-slate-200'>
          <Text className='text-2xl font-bold text-slate-900'>
            Lịch trình đã lưu
          </Text>
        </View>
        <View className='flex-1 items-center justify-center'>
          <ActivityIndicator size='large' color='#0066FF' />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView className='flex-1 bg-slate-50' edges={['top']}>
      <View className='px-4 py-4 bg-white border-b border-slate-200'>
        <Text className='text-2xl font-bold text-slate-900'>
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
            <Text className='text-lg font-semibold text-slate-900 mb-2'>
              Chưa có lịch trình nào
            </Text>
            <Text className='text-sm text-slate-600 text-center'>
              Lưu lịch trình từ cuộc trò chuyện để xem ở đây
            </Text>
          </View>
        ) : (
          <View className='p-4'>
            {itineraries.map((itinerary) => (
              <View
                key={itinerary.id}
                className='bg-white rounded-2xl border border-slate-200 p-4 mb-4'
              >
                <TouchableOpacity
                  onPress={() => handleViewDetail(itinerary)}
                  activeOpacity={0.7}
                >
                  <Text className='text-lg font-bold text-slate-900 mb-3'>
                    {itinerary.title}
                  </Text>

                  <View className='flex-row items-center mb-2'>
                    <View className='w-8 h-8 rounded-full bg-blue-50 items-center justify-center mr-3'>
                      <MapPin size={16} color='#0066FF' />
                    </View>
                    <Text className='text-sm text-slate-600'>
                      {itinerary.payload.destination}
                    </Text>
                  </View>

                  <View className='flex-row items-center mb-2'>
                    <View className='w-8 h-8 rounded-full bg-blue-50 items-center justify-center mr-3'>
                      <Calendar size={16} color='#0066FF' />
                    </View>
                    <Text className='text-sm text-slate-600'>
                      {itinerary.payload.duration}
                    </Text>
                  </View>

                  <View className='flex-row items-center mb-3'>
                    <View className='w-8 h-8 rounded-full bg-blue-50 items-center justify-center mr-3'>
                      <DollarSign size={16} color='#0066FF' />
                    </View>
                    <Text className='text-sm text-slate-600'>
                      {itinerary.payload.budget}
                    </Text>
                  </View>

                  <View className='pt-3 border-t border-slate-200'>
                    <Text className='text-xs text-slate-500'>
                      Đã lưu: {formatDate(itinerary.created_at)}
                    </Text>
                  </View>
                </TouchableOpacity>

                <TouchableOpacity
                  onPress={() => handleDelete(itinerary)}
                  className='absolute top-4 right-4 w-8 h-8 rounded-full bg-red-50 items-center justify-center'
                >
                  <Trash2 size={16} color='#EF4444' />
                </TouchableOpacity>
              </View>
            ))}
          </View>
        )}
      </ScrollView>

      <Modal
        visible={showDetailModal}
        animationType='slide'
        presentationStyle='pageSheet'
        onRequestClose={() => setShowDetailModal(false)}
      >
        <SafeAreaView className='flex-1 bg-slate-50' edges={['top']}>
          <View className='flex-row items-center justify-between px-4 py-4 bg-white border-b border-slate-200'>
            <Text className='text-xl font-bold text-slate-900'>
              Chi tiết lịch trình
            </Text>
            <TouchableOpacity onPress={() => setShowDetailModal(false)}>
              <X size={24} color='#64748B' />
            </TouchableOpacity>
          </View>

          <ScrollView className='flex-1'>
            {selectedItinerary && (
              <View className='p-4'>
                <View className='bg-white rounded-2xl border border-slate-200 p-4 mb-4'>
                  <Text className='text-2xl font-bold text-slate-900 mb-4'>
                    {selectedItinerary.title}
                  </Text>

                  <View className='flex-row items-center mb-3'>
                    <MapPin size={20} color='#0066FF' />
                    <Text className='text-base text-slate-900 ml-3 font-semibold'>
                      {selectedItinerary.payload.destination}
                    </Text>
                  </View>

                  <View className='flex-row items-center mb-3'>
                    <Calendar size={20} color='#0066FF' />
                    <Text className='text-base text-slate-600 ml-3'>
                      {selectedItinerary.payload.duration}
                    </Text>
                  </View>

                  <View className='flex-row items-center'>
                    <DollarSign size={20} color='#0066FF' />
                    <Text className='text-base text-slate-600 ml-3'>
                      {selectedItinerary.payload.budget}
                    </Text>
                  </View>
                </View>

                {selectedItinerary.payload.days &&
                  selectedItinerary.payload.days.length > 0 && (
                    <View>
                      <Text className='text-lg font-bold text-slate-900 mb-3'>
                        Lịch trình chi tiết
                      </Text>
                      {selectedItinerary.payload.days.map(
                        (day: any, index: number) => (
                          <View
                            key={index}
                            className='bg-white rounded-2xl border border-slate-200 p-4 mb-4'
                          >
                            <Text className='text-base font-bold text-slate-900 mb-3'>
                              Ngày {day.day} - {day.date}
                            </Text>
                            {day.activities &&
                              day.activities.map(
                                (activity: any, actIndex: number) => (
                                  <View
                                    key={actIndex}
                                    className='mb-3 pb-3 border-b border-slate-200 last:border-b-0'
                                  >
                                    <Text className='text-sm font-semibold text-slate-900'>
                                      {activity.name}
                                    </Text>
                                    {activity.time && (
                                      <Text className='text-xs text-slate-600 mt-1'>
                                        ⏰ {activity.time}
                                      </Text>
                                    )}
                                    {activity.address && (
                                      <Text className='text-xs text-slate-600 mt-1'>
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

          <View className='p-4 bg-white border-t border-slate-200'>
            <Button onPress={() => setShowDetailModal(false)}>Đóng</Button>
          </View>
        </SafeAreaView>
      </Modal>
    </SafeAreaView>
  );
}
