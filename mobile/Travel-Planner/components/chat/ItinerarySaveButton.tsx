import React from 'react';
import { View, Text, TouchableOpacity } from 'react-native';
import { Bookmark, BookmarkCheck } from 'lucide-react-native';

interface ItinerarySaveButtonProps {
  isSaved: boolean;
  onSave: () => void;
}

export function ItinerarySaveButton({
  isSaved,
  onSave,
}: ItinerarySaveButtonProps) {
  return (
    <View className='mt-2 self-start w-[80%]'>
      <TouchableOpacity
        onPress={onSave}
        className='flex-row items-center bg-blue-600 px-4 py-2 rounded-xl'
        disabled={isSaved}
      >
        {isSaved ? (
          <>
            <BookmarkCheck size={18} color='#FFFFFF' />
            <Text className='text-white font-semibold ml-2'>Đã lưu</Text>
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
