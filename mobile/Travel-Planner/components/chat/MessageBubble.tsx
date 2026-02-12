import React from 'react';
import { View, Text } from 'react-native';
import { User, Sparkles } from 'lucide-react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { useTheme } from '@/contexts/ThemeContext';

interface MessageBubbleProps {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
}

export function MessageBubble({
  role,
  content,
  timestamp,
}: MessageBubbleProps) {
  const { colors } = useTheme();
  const isUser = role === 'user';

  // Check if content has HTML tags (for assistant messages)
  const hasHTML =
    !isUser &&
    (content.includes('<b>') ||
      content.includes('</b>') ||
      content.includes('<strong>') ||
      content.includes('</strong>'));

  return (
    <View
      className={`flex-row gap-3 mb-4 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
    >
      {/* Avatar */}
      <View className='flex-shrink-0'>
        {isUser ? (
          <View
            className='w-8 h-8 rounded-full items-center justify-center'
            style={{ backgroundColor: colors.muted }}
          >
            <User size={16} color={colors.mutedForeground} />
          </View>
        ) : (
          <LinearGradient
            colors={['#0066FF', '#00C29A']}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 1 }}
            className='w-8 h-8 rounded-full items-center justify-center'
            style={{
              elevation: 2,
              shadowColor: '#000',
              shadowOffset: { width: 0, height: 1 },
              shadowOpacity: 0.2,
              shadowRadius: 2,
            }}
          >
            <Sparkles size={16} color='white' />
          </LinearGradient>
        )}
      </View>

      {/* Message Content */}
      <View className={`flex-1 ${isUser ? 'items-end' : 'items-start'}`}>
        <View
          className='max-w-[85%] px-4 py-3 rounded-2xl'
          style={{
            backgroundColor: isUser ? colors.accent : colors.card,
            borderColor: colors.border,
            borderWidth: 1,
            elevation: 1,
            shadowColor: '#000',
            shadowOffset: { width: 0, height: 1 },
            shadowOpacity: 0.05,
            shadowRadius: 2,
          }}
        >
          {hasHTML ? (
            // For HTML content, we need to parse it manually since React Native doesn't support dangerouslySetInnerHTML
            // For now, we'll strip HTML tags and display plain text
            // In production, you might want to use react-native-render-html
            <Text
              className='text-base leading-6'
              style={{ color: colors.foreground }}
            >
              {content
                .replace(/<b>|<\/b>|<strong>|<\/strong>/g, '')
                .replace(/<br\s*\/?>/g, '\n')}
            </Text>
          ) : (
            <Text
              className='text-base leading-6'
              style={{ color: colors.foreground }}
            >
              {content}
            </Text>
          )}
        </View>

        {/* Timestamp */}
        {timestamp && (
          <Text
            className={`text-xs mt-1 px-2 ${
              isUser ? 'text-right' : 'text-left'
            }`}
            style={{ color: colors.mutedForeground }}
          >
            {timestamp}
          </Text>
        )}
      </View>
    </View>
  );
}
