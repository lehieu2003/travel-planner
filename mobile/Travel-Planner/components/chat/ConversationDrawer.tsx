import React, { useEffect, useState, useRef } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  ScrollView,
  ActivityIndicator,
  Alert,
  Animated,
  Dimensions,
  TouchableWithoutFeedback,
  Modal,
  TextInput,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { X, MessageSquare, Trash2, Plus, Edit2 } from 'lucide-react-native';
import { API_ENDPOINTS, getAuthHeaders } from '@/config/api';

interface Conversation {
  id: string;
  title: string;
  updated_at: string;
}

interface ConversationDrawerProps {
  visible: boolean;
  onClose: () => void;
  currentConversationId: string | null;
  onSelectConversation: (id: string, title: string) => void;
  onNewConversation: () => void;
}

const DRAWER_WIDTH = Dimensions.get('window').width * 0.8;

export function ConversationDrawer({
  visible,
  onClose,
  currentConversationId,
  onSelectConversation,
  onNewConversation,
}: ConversationDrawerProps) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [renameModalVisible, setRenameModalVisible] = useState(false);
  const [selectedConversation, setSelectedConversation] =
    useState<Conversation | null>(null);
  const [newTitle, setNewTitle] = useState('');
  const translateX = useRef(new Animated.Value(-DRAWER_WIDTH)).current;
  const backdropOpacity = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (visible) {
      loadConversations();
      // Open drawer
      Animated.parallel([
        Animated.timing(translateX, {
          toValue: 0,
          duration: 300,
          useNativeDriver: true,
        }),
        Animated.timing(backdropOpacity, {
          toValue: 1,
          duration: 300,
          useNativeDriver: true,
        }),
      ]).start();
    } else {
      // Close drawer
      Animated.parallel([
        Animated.timing(translateX, {
          toValue: -DRAWER_WIDTH,
          duration: 250,
          useNativeDriver: true,
        }),
        Animated.timing(backdropOpacity, {
          toValue: 0,
          duration: 250,
          useNativeDriver: true,
        }),
      ]).start();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
        console.error('❌ [ConversationDrawer] Error response:', errorText);
      }
    } catch (error) {
      console.error(
        '❌ [ConversationDrawer] Error loading conversations:',
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

  const handleRename = (conversation: Conversation) => {
    setSelectedConversation(conversation);
    setNewTitle(conversation.title);
    setRenameModalVisible(true);
  };

  const submitRename = async () => {
    if (!selectedConversation || !newTitle.trim()) {
      Alert.alert('Lỗi', 'Tên không được để trống');
      return;
    }

    try {
      const headers = await getAuthHeaders();
      const response = await fetch(
        API_ENDPOINTS.CONVERSATIONS.UPDATE_TITLE(selectedConversation.id),
        {
          method: 'PATCH',
          headers,
          body: JSON.stringify({ title: newTitle.trim() }),
        },
      );

      if (response.ok) {
        setConversations((prev) =>
          prev.map((c) =>
            c.id === selectedConversation.id
              ? { ...c, title: newTitle.trim() }
              : c,
          ),
        );
        setRenameModalVisible(false);
        Alert.alert('Thành công', 'Đã đổi tên cuộc trò chuyện');
      } else {
        const errorText = await response.text();
        console.error('❌ [ConversationDrawer] Rename error:', errorText);
        Alert.alert('Lỗi', 'Không thể đổi tên cuộc trò chuyện');
      }
    } catch (error) {
      console.error('Error renaming conversation:', error);
      Alert.alert('Lỗi', 'Không thể đổi tên cuộc trò chuyện');
    }
  };

  const handleSelect = (conversation: Conversation) => {
    onSelectConversation(conversation.id, conversation.title);
    onClose();
  };

  const handleNewChat = () => {
    onNewConversation();
    onClose();
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

  // Log render state
  console.log(
    '🎭 [ConversationDrawer] Render - visible:',
    visible,
    'isLoading:',
    isLoading,
    'conversations:',
    conversations.length,
  );

  if (!visible) return null;

  return (
    <View className='absolute inset-0 z-50'>
      {/* Backdrop */}
      <TouchableWithoutFeedback onPress={onClose}>
        <Animated.View
          className='absolute inset-0 bg-black'
          style={{
            opacity: backdropOpacity.interpolate({
              inputRange: [0, 1],
              outputRange: [0, 0.5],
            }),
          }}
        />
      </TouchableWithoutFeedback>

      {/* Drawer */}
      <Animated.View
        className='absolute top-0 bottom-0 left-0 bg-white'
        style={{
          width: DRAWER_WIDTH,
          transform: [{ translateX }],
        }}
      >
        <SafeAreaView className='flex-1' edges={['top', 'bottom']}>
          {/* Header */}
          <View className='border-b border-slate-200 p-4 space-y-3'>
            <View className='flex-row items-center justify-between'>
              <Text className='text-lg font-bold text-slate-900'>
                Travel Planner
              </Text>
              <TouchableOpacity onPress={onClose}>
                <X size={24} color='#64748B' />
              </TouchableOpacity>
            </View>

            <TouchableOpacity
              onPress={handleNewChat}
              className='bg-blue-600 rounded-xl py-3 px-4 flex-row items-center justify-center'
              activeOpacity={0.7}
            >
              <Plus size={20} color='white' />
              <Text className='text-white font-semibold ml-2'>
                Trò chuyện mới
              </Text>
            </TouchableOpacity>
          </View>

          {/* Conversations List */}
          {isLoading ? (
            <View className='flex-1 items-center justify-center'>
              <ActivityIndicator size='large' color='#0066FF' />
            </View>
          ) : conversations.length === 0 ? (
            <View className='flex-1 items-center justify-center p-8'>
              <MessageSquare size={48} color='#CBD5E1' />
              <Text className='text-lg font-semibold text-slate-900 mt-4 mb-2'>
                Chưa có cuộc trò chuyện nào
              </Text>
              <Text className='text-sm text-slate-600 text-center'>
                Bắt đầu trò chuyện mới để lên kế hoạch du lịch
              </Text>
            </View>
          ) : (
            <ScrollView className='flex-1 p-3'>
              {conversations.map((conversation, index) => {
                console.log(
                  `🎨 [ConversationDrawer] Rendering conversation ${index}:`,
                  {
                    id: conversation.id,
                    title: conversation.title,
                  },
                );
                const isActive = currentConversationId === conversation.id;
                return (
                  <View key={conversation.id} className='mb-2'>
                    <TouchableOpacity
                      onPress={() => handleSelect(conversation)}
                      className={`rounded-xl p-3 border ${
                        isActive
                          ? 'bg-blue-50 border-blue-200'
                          : 'bg-white border-slate-200'
                      }`}
                      activeOpacity={0.7}
                    >
                      <View className='flex-row items-start gap-3'>
                        <View className='mt-1'>
                          <MessageSquare
                            size={16}
                            color={isActive ? '#2563EB' : '#64748B'}
                          />
                        </View>
                        <View className='flex-1 min-w-0'>
                          <Text
                            className={`font-medium ${
                              isActive ? 'text-blue-900' : 'text-slate-900'
                            }`}
                            numberOfLines={2}
                          >
                            {conversation.title}
                          </Text>
                          <Text className='text-xs text-slate-500 mt-1'>
                            {formatDate(conversation.updated_at)}
                          </Text>
                        </View>
                        <View className='flex-row items-center gap-2'>
                          <TouchableOpacity
                            onPress={() => handleRename(conversation)}
                          >
                            <Edit2 size={16} color='#64748B' />
                          </TouchableOpacity>
                          <TouchableOpacity
                            onPress={() => handleDelete(conversation)}
                          >
                            <Trash2 size={16} color='#EF4444' />
                          </TouchableOpacity>
                        </View>
                      </View>
                    </TouchableOpacity>
                  </View>
                );
              })}
            </ScrollView>
          )}
        </SafeAreaView>
      </Animated.View>

      {/* Rename Modal */}
      <Modal
        visible={renameModalVisible}
        transparent
        animationType='fade'
        onRequestClose={() => setRenameModalVisible(false)}
      >
        <KeyboardAvoidingView
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
          className='flex-1'
        >
          <TouchableWithoutFeedback
            onPress={() => setRenameModalVisible(false)}
          >
            <View className='flex-1 bg-black/50 justify-center items-center p-4'>
              <TouchableWithoutFeedback>
                <View className='bg-white rounded-2xl p-6 w-full max-w-sm'>
                  <Text className='text-lg font-bold text-slate-900 mb-2'>
                    Đổi tên cuộc trò chuyện
                  </Text>
                  <Text className='text-sm text-slate-600 mb-4'>
                    Nhập tên mới cho cuộc trò chuyện
                  </Text>

                  <TextInput
                    className='bg-slate-100 rounded-xl px-4 py-3 text-slate-900 mb-6'
                    value={newTitle}
                    onChangeText={setNewTitle}
                    placeholder='Nhập tên mới...'
                    placeholderTextColor='#94A3B8'
                    autoFocus
                    onSubmitEditing={submitRename}
                  />

                  <View className='flex-row gap-3'>
                    <TouchableOpacity
                      onPress={() => setRenameModalVisible(false)}
                      className='flex-1 bg-slate-100 rounded-xl py-3 px-4'
                      activeOpacity={0.7}
                    >
                      <Text className='text-center font-semibold text-slate-700'>
                        Hủy
                      </Text>
                    </TouchableOpacity>

                    <TouchableOpacity
                      onPress={submitRename}
                      className='flex-1 bg-blue-600 rounded-xl py-3 px-4'
                      activeOpacity={0.7}
                    >
                      <Text className='text-center font-semibold text-white'>
                        Lưu
                      </Text>
                    </TouchableOpacity>
                  </View>
                </View>
              </TouchableWithoutFeedback>
            </View>
          </TouchableWithoutFeedback>
        </KeyboardAvoidingView>
      </Modal>
    </View>
  );
}
