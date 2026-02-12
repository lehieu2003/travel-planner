import React, { useEffect, useRef } from 'react';
import { View, Text, Animated } from 'react-native';
import { Sparkles } from 'lucide-react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { useTheme } from '@/contexts/ThemeContext';

export function TypingIndicator() {
  const { colors } = useTheme();
  const dot1Opacity = useRef(new Animated.Value(0.3)).current;
  const dot2Opacity = useRef(new Animated.Value(0.3)).current;
  const dot3Opacity = useRef(new Animated.Value(0.3)).current;

  useEffect(() => {
    const createAnimation = (animatedValue: Animated.Value, delay: number) => {
      return Animated.loop(
        Animated.sequence([
          Animated.timing(animatedValue, {
            toValue: 1,
            duration: 600,
            delay,
            useNativeDriver: true,
          }),
          Animated.timing(animatedValue, {
            toValue: 0.3,
            duration: 600,
            useNativeDriver: true,
          }),
        ]),
      );
    };

    const animation1 = createAnimation(dot1Opacity, 0);
    const animation2 = createAnimation(dot2Opacity, 200);
    const animation3 = createAnimation(dot3Opacity, 400);

    animation1.start();
    animation2.start();
    animation3.start();

    return () => {
      animation1.stop();
      animation2.stop();
      animation3.stop();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <View className='flex-row gap-3 mb-4'>
      {/* AI Avatar */}
      <View className='flex-shrink-0'>
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
      </View>

      {/* Typing Bubble */}
      <View
        className='rounded-2xl px-5 py-3'
        style={{
          backgroundColor: colors.card,
          borderColor: colors.border,
          borderWidth: 1,
          elevation: 1,
          shadowColor: '#000',
          shadowOffset: { width: 0, height: 1 },
          shadowOpacity: 0.05,
          shadowRadius: 2,
        }}
      >
        <View className='flex-row items-center gap-2'>
          <Text className='text-sm' style={{ color: colors.mutedForeground }}>
            TravelGPT đang viết
          </Text>
          <View className='flex-row gap-1'>
            <Animated.View
              className='w-1.5 h-1.5 rounded-full'
              style={{ opacity: dot1Opacity, backgroundColor: colors.primary }}
            />
            <Animated.View
              className='w-1.5 h-1.5 rounded-full'
              style={{ opacity: dot2Opacity, backgroundColor: colors.primary }}
            />
            <Animated.View
              className='w-1.5 h-1.5 rounded-full'
              style={{ opacity: dot3Opacity, backgroundColor: colors.primary }}
            />
          </View>
        </View>
      </View>
    </View>
  );
}
