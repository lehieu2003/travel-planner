import {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useColorScheme } from 'react-native';

type Theme = 'light' | 'dark' | 'system';

interface ThemeContextType {
  theme: Theme;
  activeTheme: 'light' | 'dark';
  toggleTheme: () => void;
  setTheme: (theme: Theme) => void;
  colors: ColorScheme;
}

interface ColorScheme {
  background: string;
  foreground: string;
  card: string;
  cardForeground: string;
  primary: string;
  primaryForeground: string;
  secondary: string;
  secondaryForeground: string;
  muted: string;
  mutedForeground: string;
  accent: string;
  accentForeground: string;
  destructive: string;
  destructiveForeground: string;
  border: string;
  input: string;
  inputBackground: string;
  ring: string;
}

const lightColors: ColorScheme = {
  background: '#ffffff',
  foreground: '#0f172a',
  card: '#ffffff',
  cardForeground: '#0f172a',
  primary: '#0066ff',
  primaryForeground: '#ffffff',
  secondary: '#00c29a',
  secondaryForeground: '#ffffff',
  muted: '#f1f5f9',
  mutedForeground: '#64748b',
  accent: '#f1f5f9',
  accentForeground: '#0f172a',
  destructive: '#ef4444',
  destructiveForeground: '#ffffff',
  border: '#e2e8f0',
  input: '#f1f5f9',
  inputBackground: '#ffffff',
  ring: '#0066ff',
};

const darkColors: ColorScheme = {
  background: '#0f172a',
  foreground: '#f1f5f9',
  card: '#1e293b',
  cardForeground: '#f1f5f9',
  primary: '#0066ff',
  primaryForeground: '#ffffff',
  secondary: '#00c29a',
  secondaryForeground: '#ffffff',
  muted: '#334155',
  mutedForeground: '#94a3b8',
  accent: '#334155',
  accentForeground: '#f1f5f9',
  destructive: '#ef4444',
  destructiveForeground: '#ffffff',
  border: 'rgba(255, 255, 255, 0.1)',
  input: 'rgba(255, 255, 255, 0.05)',
  inputBackground: '#1e293b',
  ring: '#0066ff',
};

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

const THEME_STORAGE_KEY = '@app_theme';

export function ThemeProvider({ children }: { children: ReactNode }) {
  const systemColorScheme = useColorScheme();
  const [theme, setThemeState] = useState<Theme>('system');
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    loadTheme();
  }, []);

  const loadTheme = async () => {
    try {
      const savedTheme = await AsyncStorage.getItem(THEME_STORAGE_KEY);
      if (
        savedTheme &&
        (savedTheme === 'light' ||
          savedTheme === 'dark' ||
          savedTheme === 'system')
      ) {
        setThemeState(savedTheme as Theme);
      }
    } catch (error) {
      console.error('Error loading theme:', error);
    } finally {
      setIsLoaded(true);
    }
  };

  const activeTheme: 'light' | 'dark' =
    theme === 'system'
      ? systemColorScheme === 'dark'
        ? 'dark'
        : 'light'
      : theme;

  const colors = activeTheme === 'dark' ? darkColors : lightColors;

  const toggleTheme = () => {
    const newTheme = activeTheme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
  };

  const setTheme = async (newTheme: Theme) => {
    try {
      setThemeState(newTheme);
      await AsyncStorage.setItem(THEME_STORAGE_KEY, newTheme);
    } catch (error) {
      console.error('Error saving theme:', error);
    }
  };

  if (!isLoaded) {
    return null; // or a loading spinner
  }

  return (
    <ThemeContext.Provider
      value={{ theme, activeTheme, toggleTheme, setTheme, colors }}
    >
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}
