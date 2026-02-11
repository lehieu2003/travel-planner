// Common types used across the app

export type Gender = 'male' | 'female' | 'other' | null;
export type EnergyLevel = 'low' | 'medium' | 'high' | null;

export interface TravelPreference {
  id: string;
  label: string;
  icon: string;
  color: string;
}

export interface User {
  id: string;
  email: string;
  full_name?: string;
  age?: number;
  gender?: Gender;
  energy_level?: EnergyLevel;
  budget_min?: number;
  budget_max?: number;
  preferences?: string[];
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  itineraryData?: ItineraryData | null;
}

export interface ItineraryData {
  destination: string;
  duration: string;
  budget: string;
  days?: DayItinerary[];
  total_cost?: number;
}

export interface DayItinerary {
  day: number;
  date: string;
  activities: Activity[];
}

export interface Activity {
  time: string;
  title: string;
  description?: string;
  location?: string;
  cost?: number;
}

export interface Conversation {
  id: string;
  title: string;
  date: string;
  updated_at?: string;
  created_at?: string;
}

export interface SavedItinerary {
  id: number;
  conversation_id: string;
  destination: string;
  duration: string;
  budget: string;
  itinerary_data: ItineraryData;
  created_at: string;
}
