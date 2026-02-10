import { useState, useRef, useEffect } from 'react';
import { Send, Menu, ChevronDown, User, LogOut, BookMarked, Calendar } from 'lucide-react';
import { ConversationSidebar, type Conversation } from './ConversationSidebar';
import { ChatMessage, TypingIndicator, type Message, type ItineraryData } from './ChatMessage';
import { ItineraryPanel } from './ItineraryPanel';
import { Button } from './ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from './ui/dropdown-menu';
import { Avatar, AvatarFallback } from './ui/avatar';
import { motion, AnimatePresence } from 'motion/react';
import { API_ENDPOINTS, getAuthHeaders } from '../config/api';

interface MultiChatInterfaceProps {
  onNavigate?: (page: 'profile' | 'itineraries') => void;
  onLogout?: () => void;
}

// Helper to format date from ISO string
const formatDate = (dateStr: string) => {
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString('vi-VN');
  } catch {
    return dateStr;
  }
};

// Helper to format time from ISO string
const formatTime = (dateStr: string) => {
  try {
    const date = new Date(dateStr);
    return date.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
};

// Quick prompt suggestions
const quickPrompts = [
  '5 triệu đi Đà Lạt 3 ngày',
  'Đi Hà Nội cuối tuần này, thích cà phê',
  'Phú Quốc 2 ngày 1 đêm — lịch chill',
  'Sapa mùa đông ngân sách 7 triệu',
];

export function MultiChatInterface({ onNavigate, onLogout }: MultiChatInterfaceProps) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [showQuickPrompts, setShowQuickPrompts] = useState(true);
  const [showItinerary, setShowItinerary] = useState(false);
  const [isLoadingConversations, setIsLoadingConversations] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    };

    if (isDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isDropdownOpen]);

  // Check if current messages have itinerary data with days
  const hasItinerary = messages.some((msg) => 
    msg.itineraryData && 
    msg.itineraryData.days && 
    msg.itineraryData.days.length > 0
  );
  
  // Helper to find itinerary data
  const getItineraryData = () => {
    // Find the most recent message with itinerary data
    const messageWithItinerary = [...messages]
      .reverse()
      .find(m => m.itineraryData && m.itineraryData.days && m.itineraryData.days.length > 0);
    
    if (messageWithItinerary?.itineraryData) {
      console.log('getItineraryData found:', {
        messageId: messageWithItinerary.id,
        destination: messageWithItinerary.itineraryData.destination,
        daysCount: messageWithItinerary.itineraryData.days?.length || 0,
      });
    } else {
      console.log('getItineraryData: No itinerary found in messages', {
        totalMessages: messages.length,
        messagesWithItinerary: messages.filter(m => m.itineraryData).length,
      });
    }
    
    return messageWithItinerary?.itineraryData;
  };

  // Get itinerary key for force re-render
  const itineraryKey = getItineraryData() 
    ? `${getItineraryData()?.destination}-${getItineraryData()?.days?.length || 0}-${messages.length}`
    : 'no-itinerary';

  // Update showItinerary when conversation changes
  useEffect(() => {
    setShowItinerary(hasItinerary);
  }, [hasItinerary]);

  // Load conversations on mount
  useEffect(() => {
    loadConversations();
  }, []);

  // Load messages when conversation is selected
  useEffect(() => {
    if (activeConversationId) {
      loadMessages(activeConversationId);
    } else {
      setMessages([]);
      setShowQuickPrompts(true);
    }
  }, [activeConversationId]);

  const loadConversations = async () => {
    try {
      setIsLoadingConversations(true);
      const response = await fetch(API_ENDPOINTS.CONVERSATIONS.LIST, {
        headers: getAuthHeaders(),
      });

      if (!response.ok) {
        if (response.status === 401) {
          onLogout?.();
          return;
        }
        throw new Error('Failed to load conversations');
      }

      const data = await response.json();
      const formattedConversations: Conversation[] = data.map((conv: any) => ({
        id: conv.id,
        title: conv.title,
        date: formatDate(conv.updated_at || conv.created_at),
      }));

      setConversations(formattedConversations);
      
      // Auto-select first conversation if available
      if (formattedConversations.length > 0 && !activeConversationId) {
        setActiveConversationId(formattedConversations[0].id);
      }
    } catch (error) {
      console.error('Error loading conversations:', error);
    } finally {
      setIsLoadingConversations(false);
    }
  };

  const loadMessages = async (conversationId: string) => {
    try {
      const response = await fetch(API_ENDPOINTS.CONVERSATIONS.GET_MESSAGES(conversationId), {
        headers: getAuthHeaders(),
      });

      if (!response.ok) {
        if (response.status === 401) {
          onLogout?.();
          return;
        }
        throw new Error('Failed to load messages');
      }

      const data = await response.json();
      const formattedMessages: Message[] = data.map((msg: any) => {
        const message: Message = {
          id: msg.id,
          role: msg.role,
          content: msg.content,
          timestamp: formatTime(msg.created_at),
          itineraryData: msg.itinerary_data || msg.itineraryData || null,
        };
        
        // Debug: log if itinerary data exists
        if (message.itineraryData) {
          console.log('Found itinerary data in message:', {
            messageId: message.id,
            hasDays: !!message.itineraryData.days,
            daysCount: message.itineraryData.days?.length || 0,
            itineraryData: message.itineraryData
          });
        }
        
        return message;
      });

      setMessages(formattedMessages);
      setShowQuickPrompts(formattedMessages.length <= 1);
    } catch (error) {
      console.error('Error loading messages:', error);
    }
  };

  const handleNewConversation = async () => {
    try {
      const response = await fetch(API_ENDPOINTS.CONVERSATIONS.CREATE, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ title: 'Cuộc trò chuyện mới' }),
      });

      if (!response.ok) {
        if (response.status === 401) {
          onLogout?.();
          return;
        }
        throw new Error('Failed to create conversation');
      }

      const newConv = await response.json();
      const formattedConv: Conversation = {
        id: newConv.id,
        title: newConv.title,
        date: formatDate(newConv.created_at),
      };

      setConversations([formattedConv, ...conversations]);
      setActiveConversationId(newConv.id);
      setMessages([
        {
          id: `m-${Date.now()}`,
          role: 'assistant',
          content: 'Hãy nói cho mình biết bạn muốn đi đâu và ngân sách thế nào nhé ✈️✨',
          timestamp: new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
      setShowQuickPrompts(true);
      setIsSidebarOpen(false);
    } catch (error) {
      console.error('Error creating conversation:', error);
    }
  };

  const handleSelectConversation = (id: string) => {
    setActiveConversationId(id);
    // Messages will be loaded by useEffect
  };

  const handleRenameConversation = async (id: string, newTitle: string) => {
    try {
      const response = await fetch(API_ENDPOINTS.CONVERSATIONS.UPDATE_TITLE(id), {
        method: 'PATCH',
        headers: getAuthHeaders(),
        body: JSON.stringify({ title: newTitle }),
      });

      if (!response.ok) {
        if (response.status === 401) {
          onLogout?.();
          return;
        }
        throw new Error('Failed to update conversation title');
      }

      setConversations(conversations.map((c) => (c.id === id ? { ...c, title: newTitle } : c)));
    } catch (error) {
      console.error('Error renaming conversation:', error);
    }
  };

  const handleDeleteConversation = async (id: string) => {
    try {
      const response = await fetch(API_ENDPOINTS.CONVERSATIONS.DELETE(id), {
        method: 'DELETE',
        headers: getAuthHeaders(),
      });

      if (!response.ok) {
        if (response.status === 401) {
          onLogout?.();
          return;
        }
        throw new Error('Failed to delete conversation');
      }

      setConversations(conversations.filter((c) => c.id !== id));
      if (activeConversationId === id) {
        const remaining = conversations.filter((c) => c.id !== id);
        setActiveConversationId(remaining[0]?.id || null);
        setMessages([]);
      }
    } catch (error) {
      console.error('Error deleting conversation:', error);
    }
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return;

    const messageContent = inputValue;
    setInputValue('');
    setShowQuickPrompts(false);
    setIsTyping(true);

    // Add user message optimistically (will be reloaded from server)
    const tempUserMessage: Message = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: messageContent,
      timestamp: new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages((prev) => [...prev, tempUserMessage]);

    try {
      // Gọi API planning với authentication
      const response = await fetch(API_ENDPOINTS.PLAN.GENERATE, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          message: messageContent,
          conversation_id: activeConversationId,
        }),
      });

      if (!response.ok) {
        if (response.status === 401) {
          // Token không hợp lệ, logout
          onLogout?.();
          return;
        }
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Đã có lỗi xảy ra');
      }

      const data = await response.json();

      // Update conversation_id if this was a new conversation
      if (data.conversation_id && data.conversation_id !== activeConversationId) {
        setActiveConversationId(data.conversation_id);
        // Reload conversations to get the new one
        loadConversations();
      }

      // Handle different response types from backend
      if (data.ok && data.is_list) {
        // Case 1: User requested a simple list (restaurants, hotels, activities)
        // Reload messages to get the latest from server (includes both user and assistant messages)
        if (data.conversation_id) {
          await loadMessages(data.conversation_id);
          await loadConversations();
        } else {
          // Fallback: create message locally if no conversation_id
          const aiMessage: Message = {
            id: `m-${Date.now()}`,
            role: 'assistant',
            content: data.list_message || 'Đây là danh sách bạn yêu cầu:',
            timestamp: new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }),
          };
          setMessages((prev) => [...prev, aiMessage]);
        }
      } else if (data.ok && data.itinerary) {
        // Case 2: Successfully generated itinerary
        // Use itinerary from response immediately, then reload messages to sync
        if (data.conversation_id) {
          // First, update messages with itinerary from response to show immediately
          setMessages((prev) => {
            // Remove any temporary user message
            const filtered = prev.filter(msg => !msg.id.startsWith('temp-'));
            // Add/update assistant message with itinerary
            const existingAssistantIndex = filtered.findIndex(
              (msg, idx) => msg.role === 'assistant' && idx === filtered.length - 1
            );
            
            const itineraryMessage: Message = {
              id: `itinerary-${Date.now()}`,
              role: 'assistant',
              content: `Tuyệt vời! Mình đã chuẩn bị một lịch trình ${data.itinerary.duration} tại ${data.itinerary.destination} với ngân sách ${data.itinerary.budget} cho bạn. Đây là kế hoạch chi tiết:`,
              timestamp: new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }),
              itineraryData: data.itinerary,
            };
            
            if (existingAssistantIndex >= 0) {
              // Replace last assistant message if it exists
              filtered[existingAssistantIndex] = itineraryMessage;
              return filtered;
            } else {
              // Add new assistant message
              return [...filtered, itineraryMessage];
            }
          });
          
          // Show itinerary panel immediately
          setShowItinerary(true);
          
          // Wait a bit to ensure backend has saved the message, then reload
          setTimeout(async () => {
            await loadMessages(data.conversation_id);
            // Reload conversations to update title if needed
            await loadConversations();
            // Ensure itinerary panel is still shown after reload
            setShowItinerary(true);
          }, 500);
        } else {
          // Fallback: create message locally if no conversation_id
          const aiMessage: Message = {
            id: `m-${Date.now()}`,
            role: 'assistant',
            content: `Tuyệt vời! Mình đã chuẩn bị một lịch trình ${data.itinerary.duration} tại ${data.itinerary.destination} với ngân sách ${data.itinerary.budget} cho bạn. Đây là kế hoạch chi tiết:`,
            timestamp: new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }),
            itineraryData: data.itinerary,
          };
          setMessages((prev) => [...prev, aiMessage]);
          setShowItinerary(true);
        }
      } else if (data.ok && (data.requires_clarification || data.requires_confirmation)) {
        // Case 2: Backend needs clarification or confirmation
        // Reload messages from server to get the clarification/confirmation message
        if (data.conversation_id) {
          await loadMessages(data.conversation_id);
          await loadConversations();
        } else {
          // Fallback: show message directly if no conversation_id
          const messageText = data.clarification_message || data.confirmation_message || 'Vui lòng cung cấp thêm thông tin.';
          const aiMessage: Message = {
            id: `m-${Date.now()}`,
            role: 'assistant',
            content: messageText,
            timestamp: new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }),
          };
          setMessages((prev) => [...prev, aiMessage]);
        }
      } else {
        // Case 3: Unexpected response format
        throw new Error('Không nhận được dữ liệu lịch trình');
      }
    } catch (error) {
      // Hiển thị lỗi cho user
      const errorMessage: Message = {
        id: `m-${Date.now()}`,
        role: 'assistant',
        content: `Xin lỗi, đã có lỗi xảy ra: ${error instanceof Error ? error.message : 'Lỗi không xác định'}. Vui lòng thử lại.`,
        timestamp: new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleQuickPrompt = (prompt: string) => {
    setInputValue(prompt);
    setShowQuickPrompts(false);
  };

  const handleSaveItinerary = (data: ItineraryData) => {
    alert(`Đã lưu lịch trình: ${data.destination}`);
  };

  const activeConversation = conversations.find((c) => c.id === activeConversationId);

  return (
    <div className="h-screen flex flex-col bg-background">
      {/* Top Header */}
      <header className="bg-white border-b border-border px-4 md:px-6 py-4 flex items-center justify-between shadow-sm z-50 relative">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden"
            onClick={() => setIsSidebarOpen(true)}
          >
            <Menu className="h-5 w-5" />
          </Button>
          <h1 className="bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
            Travel Planner GPT
          </h1>
        </div>
        
        {/* Itinerary Toggle Button - Mobile */}
        {hasItinerary && (
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            onClick={() => setShowItinerary(!showItinerary)}
          >
            <Calendar className="h-5 w-5" />
          </Button>
        )}

        <div className="relative z-[100]" ref={dropdownRef}>
          <Button 
            variant="ghost" 
            className="flex items-center gap-2 hover:bg-muted rounded-xl"
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
          >
            <Avatar className="h-8 w-8">
              <AvatarFallback className="bg-primary text-white">U</AvatarFallback>
            </Avatar>
            <ChevronDown className={`h-4 w-4 text-muted-foreground transition-transform ${isDropdownOpen ? 'rotate-180' : ''}`} />
          </Button>
          
          {isDropdownOpen && (
            <div className="absolute right-0 top-full mt-2 w-48 rounded-xl bg-white border shadow-lg z-[100] py-1 animate-in fade-in-0 zoom-in-95">
              <button
                onClick={() => {
                  setIsDropdownOpen(false);
                  onNavigate?.('profile');
                }}
                className="w-full flex items-center gap-2 px-4 py-2 hover:bg-muted rounded-lg cursor-pointer text-left"
              >
                <User className="h-4 w-4" />
                Hồ sơ cá nhân
              </button>
              <button
                onClick={() => {
                  setIsDropdownOpen(false);
                  onNavigate?.('itineraries');
                }}
                className="w-full flex items-center gap-2 px-4 py-2 hover:bg-muted rounded-lg cursor-pointer text-left"
              >
                <BookMarked className="h-4 w-4" />
                Lịch trình đã lưu
              </button>
              <div className="h-px bg-border my-1" />
              <button
                onClick={() => {
                  setIsDropdownOpen(false);
                  onLogout?.();
                }}
                className="w-full flex items-center gap-2 px-4 py-2 hover:bg-muted rounded-lg cursor-pointer text-left text-destructive"
              >
                <LogOut className="h-4 w-4" />
                Đăng xuất
              </button>
            </div>
          )}
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        <ConversationSidebar
          conversations={conversations}
          activeConversationId={activeConversationId}
          onSelectConversation={handleSelectConversation}
          onNewConversation={handleNewConversation}
          onRenameConversation={handleRenameConversation}
          onDeleteConversation={handleDeleteConversation}
          isMobileOpen={isSidebarOpen}
          onMobileClose={() => setIsSidebarOpen(false)}
        />

        {/* Chat Panel */}
        <div className="flex-1 flex flex-col bg-background overflow-hidden min-h-0">
          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto px-4 md:px-6 py-6 min-h-0">
            <div className="max-w-4xl mx-auto">
              {isLoadingConversations ? (
                <div className="flex items-center justify-center h-full">
                  <p className="text-muted-foreground">Đang tải...</p>
                </div>
              ) : messages.length === 0 && !activeConversationId ? (
                <div className="flex flex-col items-center justify-center h-full text-center">
                  <p className="text-muted-foreground mb-4">
                    Chào mừng đến với Travel Planner GPT! 👋
                  </p>
                  <p className="text-muted-foreground mb-6">
                    Hãy tạo cuộc trò chuyện mới để bắt đầu lên kế hoạch du lịch của bạn.
                  </p>
                </div>
              ) : (
                <>
                  {messages.map((message) => (
                    <ChatMessage
                      key={message.id}
                      message={message}
                    />
                  ))}
                  {isTyping && <TypingIndicator />}
                </>
              )}

              {/* Quick Prompts */}
              <AnimatePresence>
                {showQuickPrompts && messages.length <= 1 && (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -20 }}
                    className="mt-6 space-y-3"
                  >
                    <p className="text-center text-muted-foreground">
                      Gợi ý nhanh:
                    </p>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                      {quickPrompts.map((prompt, idx) => (
                        <motion.button
                          key={idx}
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: idx * 0.1 }}
                          onClick={() => handleQuickPrompt(prompt)}
                          className="px-4 py-3 bg-white hover:bg-primary/5 border border-border rounded-xl transition-all duration-200 hover:border-primary/30 hover:shadow-sm text-left"
                        >
                          {prompt}
                        </motion.button>
                      ))}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* Input Area */}
          <div className="border-t border-border bg-white px-4 md:px-6 py-4">
            <div className="max-w-4xl mx-auto">
              <div className="flex gap-2 items-end">
                <div className="flex-1 relative">
                  <textarea
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleSendMessage();
                      }
                    }}
                    placeholder="Nhập yêu cầu du lịch của bạn…"
                    rows={1}
                    className="w-full px-4 py-3 pr-12 border border-border rounded-xl focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary resize-none bg-white transition-all duration-200"
                    style={{ maxHeight: '120px' }}
                  />
                </div>
                <Button
                  onClick={handleSendMessage}
                  disabled={!inputValue.trim()}
                  className="h-12 px-6 bg-primary hover:bg-primary/90 text-white rounded-xl transition-all duration-200 hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Send className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>
        </div>

        {/* Itinerary Panel - Right Side (Desktop) / Modal (Mobile) */}
        <AnimatePresence>
          {showItinerary && hasItinerary && (
            <>
              {/* Desktop: Side Panel */}
              <motion.div
                key={itineraryKey}
                initial={{ x: '100%' }}
                animate={{ x: 0 }}
                exit={{ x: '100%' }}
                transition={{ type: 'spring', damping: 30, stiffness: 300 }}
                className="hidden lg:block w-[400px] xl:w-[450px] border-l border-border bg-white relative z-10"
              >
                <ItineraryPanel 
                  key={itineraryKey}
                  itineraryData={getItineraryData()}
                  onClose={() => setShowItinerary(false)}
                  onSaveSuccess={() => {
                    // Refresh profile stats if user navigates to profile
                    // This will be handled by Profile component itself
                  }}
                />
              </motion.div>
              
              {/* Mobile: Full Screen Modal */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="lg:hidden fixed inset-0 bg-black/50 z-50"
                onClick={() => setShowItinerary(false)}
              >
                <motion.div
                  key={itineraryKey}
                  initial={{ y: '100%' }}
                  animate={{ y: 0 }}
                  exit={{ y: '100%' }}
                  transition={{ type: 'spring', damping: 30, stiffness: 300 }}
                  className="absolute bottom-0 left-0 right-0 top-0 bg-white rounded-t-3xl overflow-hidden"
                  onClick={(e) => e.stopPropagation()}
                >
                  <ItineraryPanel 
                    key={itineraryKey}
                    itineraryData={getItineraryData()}
                    onClose={() => setShowItinerary(false)}
                    onSaveSuccess={() => {
                      // Refresh profile stats if user navigates to profile
                      // This will be handled by Profile component itself
                    }}
                  />
                </motion.div>
              </motion.div>
            </>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}