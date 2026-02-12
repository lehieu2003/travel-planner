import { View, ScrollView, KeyboardAvoidingView, Platform } from 'react-native';
import { useState, useRef, useEffect } from 'react';
import { SafeAreaView } from 'react-native-safe-area-context';
import {
  MessageBubble,
  ItinerarySaveButton,
  ItineraryCard,
  ChatInput,
  ChatHeader,
  ConversationDrawer,
  EmptyState,
  TypingIndicator,
} from '@/components/chat';
import { useChatMessages, useItinerarySave } from '@/hooks';

export default function ChatScreen() {
  const [inputValue, setInputValue] = useState('');
  const [showDrawer, setShowDrawer] = useState(false);
  const scrollViewRef = useRef<ScrollView>(null);

  const {
    messages,
    isTyping,
    conversationId,
    conversationTitle,
    sendMessage,
    clearConversation,
    switchConversation,
  } = useChatMessages();

  const { savedItineraryIds, saveItinerary, resetSavedIds } =
    useItinerarySave();

  useEffect(() => {
    scrollViewRef.current?.scrollToEnd({ animated: true });
  }, [messages]);

  const handleSend = async () => {
    if (!inputValue.trim()) return;

    const message = inputValue.trim();
    setInputValue('');
    await sendMessage(message);
  };

  const handleNewConversation = () => {
    clearConversation();
    resetSavedIds();
  };

  const handleSelectConversation = async (id: string, title: string) => {
    resetSavedIds();
    await switchConversation(id, title);
  };

  return (
    <SafeAreaView className='flex-1 bg-slate-50' edges={['top']}>
      <ChatHeader
        conversationTitle={conversationTitle}
        onShowConversations={() => {
          setShowDrawer(true);
        }}
        onNewConversation={handleNewConversation}
      />

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
            <>
              <EmptyState />
            </>
          ) : (
            <>
              {messages.map((message, index) => {
                return (
                  <View key={index} className='w-full mb-2'>
                    <MessageBubble
                      role={message.role}
                      content={message.content}
                      timestamp={message.timestamp}
                    />
                    {message.itineraryData && (
                      <View className='mt-3'>
                        <ItineraryCard itineraryData={message.itineraryData} />
                        <ItinerarySaveButton
                          isSaved={savedItineraryIds.has(`${index}`)}
                          onSave={() =>
                            saveItinerary(message.itineraryData, index)
                          }
                        />
                      </View>
                    )}
                  </View>
                );
              })}
            </>
          )}

          {isTyping && <TypingIndicator />}
        </ScrollView>

        <ChatInput
          value={inputValue}
          onChangeText={setInputValue}
          onSend={handleSend}
          disabled={isTyping}
        />
      </KeyboardAvoidingView>

      <ConversationDrawer
        visible={showDrawer}
        onClose={() => {
          setShowDrawer(false);
        }}
        currentConversationId={conversationId}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
      />
    </SafeAreaView>
  );
}
