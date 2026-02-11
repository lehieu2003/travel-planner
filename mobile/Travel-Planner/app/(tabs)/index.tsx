import {
  Text,
  View,
  ScrollView,
  TextInput,
  TouchableOpacity,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { useState, useRef, useEffect } from 'react';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Send, Loader2 } from 'lucide-react-native';

export default function ChatScreen() {
  const [messages, setMessages] = useState<
    { role: 'user' | 'assistant'; content: string }[]
  >([]);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const scrollViewRef = useRef<ScrollView>(null);

  useEffect(() => {
    // Auto scroll to bottom when messages change
    scrollViewRef.current?.scrollToEnd({ animated: true });
  }, [messages]);

  const handleSend = async () => {
    if (!inputValue.trim()) return;

    const userMessage = inputValue.trim();
    setInputValue('');

    // Add user message
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }]);
    setIsTyping(true);

    // TODO: Implement API call to backend
    // Simulate response for now
    setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content:
            'Xin chào! Đây là phiên bản demo. Tính năng chat sẽ được triển khai sau.',
        },
      ]);
      setIsTyping(false);
    }, 1000);
  };

  return (
    <SafeAreaView className='flex-1 bg-slate-50' edges={['top']}>
      <View className='flex-row items-center px-4 py-3 bg-white border-b border-slate-200'>
        <View className='w-10 h-10 rounded-xl bg-blue-600 items-center justify-center mr-3'>
          <Text className='text-xl'>✈️</Text>
        </View>
        <Text className='text-lg font-bold text-slate-900'>
          Travel Planner AI
        </Text>
      </View>

      <KeyboardAvoidingView
        className='flex-1'
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={0}
      >
        <ScrollView
          ref={scrollViewRef}
          className='flex-1'
          contentContainerStyle={{ padding: 16, flexGrow: 1 }}
        >
          {messages.length === 0 ? (
            <View className='flex-1 items-center justify-center'>
              <Text className='text-xl font-bold text-slate-900 mb-2'>
                Bắt đầu cuộc trò chuyện
              </Text>
              <Text className='text-base text-slate-600'>
                Hỏi tôi về kế hoạch du lịch của bạn!
              </Text>
            </View>
          ) : (
            messages.map((message, index) => (
              <View
                key={index}
                className={`max-w-[80%] px-4 py-3 rounded-2xl mb-3 ${
                  message.role === 'user'
                    ? 'self-end bg-blue-600'
                    : 'self-start bg-white border border-slate-200'
                }`}
              >
                <Text
                  className={`text-base leading-6 ${
                    message.role === 'user' ? 'text-white' : 'text-slate-900'
                  }`}
                >
                  {message.content}
                </Text>
              </View>
            ))
          )}

          {isTyping && (
            <View className='max-w-[80%] px-4 py-3 rounded-2xl mb-3 self-start bg-white border border-slate-200'>
              <Loader2 size={20} color='#64748B' style={{ opacity: 0.5 }} />
            </View>
          )}
        </ScrollView>

        <View className='flex-row items-end px-4 py-3 bg-white border-t border-slate-200'>
          <TextInput
            className='flex-1 max-h-24 px-4 py-3 bg-slate-50 rounded-3xl text-base text-slate-900 mr-3'
            value={inputValue}
            onChangeText={setInputValue}
            placeholder='Nhập tin nhắn...'
            placeholderTextColor='#94A3B8'
            multiline
            maxLength={500}
          />
          <TouchableOpacity
            className={`w-11 h-11 rounded-full bg-blue-600 items-center justify-center ${
              !inputValue.trim() ? 'opacity-50' : ''
            }`}
            onPress={handleSend}
            disabled={!inputValue.trim()}
          >
            <Send size={20} color='#FFFFFF' />
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
