import AsyncStorage from '@react-native-async-storage/async-storage';

// API Configuration
export const API_BASE_URL =
  'https://c31d-2402-800-6286-800f-c198-7ecb-ecfe-949d.ngrok-free.app';

export const API_ENDPOINTS = {
  AUTH: {
    LOGIN: `${API_BASE_URL}/auth/login`,
    REGISTER: `${API_BASE_URL}/auth/register`,
    ME: `${API_BASE_URL}/auth/me`,
  },
  PROFILE: {
    GET: `${API_BASE_URL}/profile/`,
    UPDATE: `${API_BASE_URL}/profile/update`,
  },
  PLAN: {
    GENERATE: `${API_BASE_URL}/plan`,
  },
  CONVERSATIONS: {
    LIST: `${API_BASE_URL}/conversations`,
    CREATE: `${API_BASE_URL}/conversations`,
    GET: (id: string) => `${API_BASE_URL}/conversations/${id}`,
    UPDATE_TITLE: (id: string) => `${API_BASE_URL}/conversations/${id}/title`,
    DELETE: (id: string) => `${API_BASE_URL}/conversations/${id}`,
    GET_MESSAGES: (id: string) =>
      `${API_BASE_URL}/conversations/${id}/messages`,
  },
  ITINERARIES: {
    LIST: `${API_BASE_URL}/itineraries`,
    SAVE: `${API_BASE_URL}/itineraries`,
    GET: (id: number) => `${API_BASE_URL}/itineraries/${id}`,
  },
};

// Helper function to get auth token from AsyncStorage
export const getAuthToken = async (): Promise<string | null> => {
  try {
    return await AsyncStorage.getItem('access_token');
  } catch (error) {
    console.error('Error getting auth token:', error);
    return null;
  }
};

// Helper function to set auth token in AsyncStorage
export const setAuthToken = async (token: string): Promise<void> => {
  try {
    await AsyncStorage.setItem('access_token', token);
  } catch (error) {
    console.error('Error setting auth token:', error);
  }
};

// Helper function to remove auth token from AsyncStorage
export const removeAuthToken = async (): Promise<void> => {
  try {
    await AsyncStorage.removeItem('access_token');
  } catch (error) {
    console.error('Error removing auth token:', error);
  }
};

// Helper function to get auth headers
export const getAuthHeaders = async (): Promise<HeadersInit> => {
  const token = await getAuthToken();
  return {
    'Content-Type': 'application/json',
    ...(token && { Authorization: `Bearer ${token}` }),
  };
};
