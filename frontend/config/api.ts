// API Configuration
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const env = (import.meta as any).env;
export const API_BASE_URL = env?.VITE_API_BASE_URL || 'http://localhost:8000';

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
    GET_MESSAGES: (id: string) => `${API_BASE_URL}/conversations/${id}/messages`,
  },
  ITINERARIES: {
    LIST: `${API_BASE_URL}/itineraries`,
    SAVE: `${API_BASE_URL}/itineraries`,
    GET: (id: number) => `${API_BASE_URL}/itineraries/${id}`,
  },
};

// Helper function to get auth token from localStorage
export const getAuthToken = (): string | null => {
  return localStorage.getItem('access_token');
};

// Helper function to set auth token in localStorage
export const setAuthToken = (token: string): void => {
  localStorage.setItem('access_token', token);
};

// Helper function to remove auth token from localStorage
export const removeAuthToken = (): void => {
  localStorage.removeItem('access_token');
};

// Helper function to get auth headers
export const getAuthHeaders = (): HeadersInit => {
  const token = getAuthToken();
  return {
    'Content-Type': 'application/json',
    ...(token && { Authorization: `Bearer ${token}` }),
  };
};

