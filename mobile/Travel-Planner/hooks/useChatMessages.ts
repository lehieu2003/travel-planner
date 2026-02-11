import { useState } from 'react';
import { Alert } from 'react-native';
import { API_ENDPOINTS, getAuthHeaders } from '@/config/api';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
  itineraryData?: any;
}

export function useChatMessages() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [conversationTitle, setConversationTitle] = useState<string>('');

  const loadMessages = async (convId: string) => {
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(
        API_ENDPOINTS.CONVERSATIONS.GET_MESSAGES(convId),
        {
          headers,
        },
      );

      if (response.ok) {
        const data = await response.json();
        setMessages(data.messages || []);
      }
    } catch (error) {
      console.error('Error loading messages:', error);
    }
  };

  const sendMessage = async (message: string) => {
    if (!message.trim()) return;

    // Add user message immediately with timestamp
    const timestamp = new Date().toLocaleTimeString('vi-VN', {
      hour: '2-digit',
      minute: '2-digit',
    });
    setMessages((prev) => [
      ...prev,
      { role: 'user', content: message, timestamp },
    ]);
    setIsTyping(true);

    try {
      const headers = await getAuthHeaders();
      const response = await fetch(API_ENDPOINTS.PLAN.GENERATE, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          message: message,
          conversation_id: conversationId,
        }),
      });

      if (!response.ok) {
        throw new Error('Không thể gửi tin nhắn');
      }

      const data = await response.json();

      // Update conversation ID if new conversation
      if (data.conversation_id && !conversationId) {
        setConversationId(data.conversation_id);
        // Set title from first message or destination
        if (data.itinerary) {
          setConversationTitle(`${data.itinerary.destination}`);
        } else {
          setConversationTitle(
            message.slice(0, 30) + (message.length > 30 ? '...' : ''),
          );
        }
      }

      // Handle different response types
      if (data.ok) {
        // Reload messages from server if needed
        if (
          data.conversation_id &&
          (data.is_list ||
            data.requires_clarification ||
            data.requires_confirmation)
        ) {
          await loadMessages(data.conversation_id);
        }
        // If itinerary is generated
        else if (data.itinerary) {
          const timestamp = new Date().toLocaleTimeString('vi-VN', {
            hour: '2-digit',
            minute: '2-digit',
          });
          setMessages((prev) => [
            ...prev,
            {
              role: 'assistant',
              content: `Tuyệt vời! Mình đã chuẩn bị một lịch trình ${data.itinerary.duration} cho ${data.itinerary.destination}!`,
              itineraryData: data.itinerary,
              timestamp,
            },
          ]);
        }
        // If it's a regular response
        else if (data.response) {
          const timestamp = new Date().toLocaleTimeString('vi-VN', {
            hour: '2-digit',
            minute: '2-digit',
          });
          setMessages((prev) => [
            ...prev,
            {
              role: 'assistant',
              content: data.response,
              timestamp,
            },
          ]);
        }
      }
    } catch (error) {
      console.error('Error sending message:', error);
      Alert.alert('Lỗi', 'Không thể gửi tin nhắn. Vui lòng thử lại.');
    } finally {
      setIsTyping(false);
    }
  };

  const clearConversation = () => {
    setConversationId(null);
    setConversationTitle('');
    setMessages([]);
  };

  const switchConversation = async (id: string, title: string) => {
    setConversationId(id);
    setConversationTitle(title);
    await loadMessages(id);
  };

  return {
    messages,
    isTyping,
    conversationId,
    conversationTitle,
    sendMessage,
    loadMessages,
    clearConversation,
    switchConversation,
  };
}
