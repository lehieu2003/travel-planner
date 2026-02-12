import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  Modal,
  TouchableOpacity,
  ScrollView,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { X, MessageSquare, Trash2 } from 'lucide-react-native';
import { API_ENDPOINTS, getAuthHeaders } from '@/config/api';
import { useTheme } from '@/contexts/ThemeContext';

interface Conversation {
  id: string;
  title: string;
  updated_at: string;
}

interface ConversationListProps {
  visible: boolean;
  onClose: () => void;
  currentConversationId: string | null;
  onSelectConversation: (id: string, title: string) => void;
}

export function ConversationList({
  visible,
  onClose,
  currentConversationId,
  onSelectConversation,
}: ConversationListProps) {
  const { colors } = useTheme();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (visible) {
      loadConversations();
    }
  }, [visible]);

  const loadConversations = async () => {
    try {
      setIsLoading(true);
      const headers = await getAuthHeaders();

      const response = await fetch(API_ENDPOINTS.CONVERSATIONS.LIST, {
        headers,
      });

      if (response.ok) {
        const data = await response.json();

        setConversations(Array.isArray(data) ? data : []);
      } else {
        const errorText = await response.text();
        console.error('❌ [ConversationList] Error response:', errorText);
      }
    } catch (error) {
      console.error(
        '❌ [ConversationList] Error loading conversations:',
        error,
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = (conversation: Conversation) => {
    Alert.alert(
      'Xóa cuộc trò chuyện',
      'Bạn có chắc chắn muốn xóa cuộc trò chuyện này?',
      [
        { text: 'Hủy', style: 'cancel' },
        {
          text: 'Xóa',
          style: 'destructive',
          onPress: async () => {
            try {
              const headers = await getAuthHeaders();
              const response = await fetch(
                API_ENDPOINTS.CONVERSATIONS.DELETE(conversation.id),
                {
                  method: 'DELETE',
                  headers,
                },
              );

              if (response.ok) {
                setConversations((prev) =>
                  prev.filter((c) => c.id !== conversation.id),
                );
                Alert.alert('Thành công', 'Đã xóa cuộc trò chuyện');
              }
            } catch (error) {
              console.error('Error deleting conversation:', error);
              Alert.alert('Lỗi', 'Không thể xóa cuộc trò chuyện');
            }
          },
        },
      ],
    );
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) {
      return date.toLocaleTimeString('vi-VN', {
        hour: '2-digit',
        minute: '2-digit',
      });
    } else if (days === 1) {
      return 'Hôm qua';
    } else if (days < 7) {
      return `${days} ngày trước`;
    } else {
      return date.toLocaleDateString('vi-VN');
    }
  };

  return (
    <Modal
      visible={visible}
      animationType='slide'
      presentationStyle='pageSheet'
      onRequestClose={onClose}
    >
      <SafeAreaView
        className='flex-1'
        edges={['top']}
        style={{ backgroundColor: colors.background }}
      >
        <View
          className='flex-row items-center justify-between px-4 py-4 border-b'
          style={{ backgroundColor: colors.card, borderColor: colors.border }}
        >
          <Text
            className='text-xl font-bold'
            style={{ color: colors.foreground }}
          >
            Cuộc trò chuyện
          </Text>
          <TouchableOpacity onPress={onClose}>
            <X size={24} color={colors.mutedForeground} />
          </TouchableOpacity>
        </View>

        {isLoading ? (
          <View className='flex-1 items-center justify-center'>
            <ActivityIndicator size='large' color={colors.primary} />
          </View>
        ) : conversations.length === 0 ? (
          <View className='flex-1 items-center justify-center p-8'>
            <MessageSquare size={48} color={colors.mutedForeground} />
            <Text
              className='text-lg font-semibold mt-4 mb-2'
              style={{ color: colors.foreground }}
            >
              Chưa có cuộc trò chuyện nào
            </Text>
            <Text
              className='text-sm text-center'
              style={{ color: colors.mutedForeground }}
            >
              Bắt đầu trò chuyện mới để lên kế hoạch du lịch
            </Text>
          </View>
        ) : (
          <ScrollView className='flex-1'>
            <View className='p-4'>
              {conversations.map((conversation) => (
                <View
                  key={conversation.id}
                  className='rounded-2xl border mb-3'
                  style={{
                    backgroundColor: colors.card,
                    borderColor:
                      currentConversationId === conversation.id
                        ? colors.primary
                        : colors.border,
                    borderWidth:
                      currentConversationId === conversation.id ? 2 : 1,
                  }}
                >
                  <TouchableOpacity
                    onPress={() => {
                      onSelectConversation(conversation.id, conversation.title);
                      onClose();
                    }}
                    className='p-4 pr-12'
                  >
                    <Text
                      className='text-base font-semibold mb-1'
                      numberOfLines={2}
                      style={{ color: colors.foreground }}
                    >
                      {conversation.title}
                    </Text>
                    <Text
                      className='text-xs'
                      style={{ color: colors.mutedForeground }}
                    >
                      {formatDate(conversation.updated_at)}
                    </Text>
                  </TouchableOpacity>

                  <TouchableOpacity
                    onPress={() => handleDelete(conversation)}
                    className='absolute top-4 right-4 w-8 h-8 rounded-full items-center justify-center'
                    style={{ backgroundColor: `${colors.destructive}20` }}
                  >
                    <Trash2 size={16} color={colors.destructive} />
                  </TouchableOpacity>
                </View>
              ))}
            </View>
          </ScrollView>
        )}
      </SafeAreaView>
    </Modal>
  );
}
