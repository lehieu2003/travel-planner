import { useState } from 'react';
import { Alert } from 'react-native';
import { API_ENDPOINTS, getAuthHeaders } from '@/config/api';

export function useItinerarySave() {
  const [savedItineraryIds, setSavedItineraryIds] = useState<Set<string>>(
    new Set(),
  );

  const saveItinerary = async (itineraryData: any, messageIndex: number) => {
    try {
      const title = `${itineraryData.destination} - ${itineraryData.duration}`;
      const payload = {
        destination: itineraryData.destination,
        duration: itineraryData.duration,
        budget: itineraryData.budget,
        days: itineraryData.days,
        hotel: itineraryData.hotel,
      };

      const headers = await getAuthHeaders();
      const response = await fetch(API_ENDPOINTS.ITINERARIES.SAVE, {
        method: 'POST',
        headers,
        body: JSON.stringify({ title, payload }),
      });

      if (response.status === 409) {
        Alert.alert('Thông báo', 'Bạn đã lưu lịch trình này rồi!');
        return;
      }

      if (response.ok) {
        setSavedItineraryIds((prev) => new Set(prev).add(`${messageIndex}`));
        Alert.alert('Thành công', 'Đã lưu lịch trình!');
      } else {
        throw new Error('Không thể lưu lịch trình');
      }
    } catch (error) {
      console.error('Error saving itinerary:', error);
      Alert.alert('Lỗi', 'Không thể lưu lịch trình. Vui lòng thử lại.');
    }
  };

  const resetSavedIds = () => {
    setSavedItineraryIds(new Set());
  };

  return {
    savedItineraryIds,
    saveItinerary,
    resetSavedIds,
  };
}
