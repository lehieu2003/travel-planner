import React from 'react';
import { View, Text, TouchableOpacity } from 'react-native';
import { Bookmark, BookmarkCheck } from 'lucide-react-native';
import { useTheme } from '@/contexts/ThemeContext';

interface ItinerarySaveButtonProps {
  isSaved: boolean;
  onSave: () => void;
}

export function ItinerarySaveButton({
  isSaved,
  onSave,
}: ItinerarySaveButtonProps) {
  const { colors } = useTheme();

  return (
    <View className='mt-2 self-start w-[80%]'>
      <TouchableOpacity
        onPress={onSave}
        className='flex-row items-center px-4 py-2 rounded-xl'
        style={{ backgroundColor: isSaved ? colors.muted : colors.primary }}
        disabled={isSaved}
      >
        {isSaved ? (
          <>
            <BookmarkCheck size={18} color={colors.foreground} />
            <Text
              className='font-semibold ml-2'
              style={{ color: colors.foreground }}
            >
              Đã lưu
            </Text>
          </>
        ) : (
          <>
            <Bookmark size={18} color='#FFFFFF' />
            <Text className='text-white font-semibold ml-2'>
              Lưu lịch trình
            </Text>
          </>
        )}
      </TouchableOpacity>
    </View>
  );
}
