import { useState, useRef, useEffect } from 'react';
import { Send, Mic, Sparkles, MapPin } from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { ItineraryPanel } from './ItineraryPanel';

interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  hasItinerary?: boolean;
}

const QUICK_PROMPTS = [
  'Tôi có 5 triệu muốn đi Đà Lạt 3 ngày',
  'Đi Hà Nội cuối tuần này, thích cà phê',
  'Đi Phú Quốc 2 ngày 1 đêm, lịch chill',
];

export function ChatScreen() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      type: 'assistant',
      content: 'Xin chào! 👋 Tôi là Travel Planner GPT - trợ lý du lịch AI của bạn. Hãy cho tôi biết bạn muốn đi đâu, ngân sách và phong cách du lịch để tôi tạo lịch trình hoàn hảo nhé!',
    },
  ]);
  const [input, setInput] = useState('');
  const [showItinerary, setShowItinerary] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = () => {
    if (!input.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: input,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');

    // Simulate AI response
    setTimeout(() => {
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: 'Tuyệt vời! Để tôi lên kế hoạch cho chuyến đi của bạn. Tôi sẽ tìm những địa điểm phù hợp với sở thích và ngân sách của bạn...',
        hasItinerary: true,
      };
      setMessages((prev) => [...prev, assistantMessage]);
      setShowItinerary(true);
    }, 1000);
  };

  const handleQuickPrompt = (prompt: string) => {
    setInput(prompt);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col lg:flex-row h-[calc(100vh-4rem)]">
      {/* Chat Panel */}
      <div className={`flex-1 flex flex-col ${showItinerary ? 'lg:border-r border-border' : ''}`}>
        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] sm:max-w-md rounded-2xl px-4 py-3 ${
                  message.type === 'user'
                    ? 'bg-[#0066FF] text-white'
                    : 'bg-white border border-border'
                }`}
              >
                {message.type === 'assistant' && (
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-6 h-6 bg-gradient-to-br from-[#0066FF] to-[#00C29A] rounded-full flex items-center justify-center">
                      <Sparkles className="w-3.5 h-3.5 text-white" />
                    </div>
                    <span className="text-muted-foreground">Travel AI</span>
                  </div>
                )}
                <p className="whitespace-pre-wrap">{message.content}</p>
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="border-t border-border bg-white p-4">
          <div className="max-w-4xl mx-auto">
            <div className="flex gap-2 items-end">
              <div className="flex-1 relative">
                <Input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Nhập yêu cầu du lịch..."
                  className="pr-12 rounded-2xl h-12 resize-none"
                />
                <button
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                  aria-label="Voice input"
                >
                  <Mic className="w-5 h-5" />
                </button>
              </div>
              <Button
                onClick={handleSend}
                disabled={!input.trim()}
                className="h-12 px-5 rounded-2xl bg-[#0066FF] hover:bg-[#0052CC]"
              >
                <Send className="w-5 h-5" />
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Right Sidebar - Tips & Quick Prompts */}
      {!showItinerary && (
        <div className="hidden lg:block w-80 xl:w-96 bg-white border-l border-border p-6 overflow-y-auto">
          <div className="space-y-6">
            <div>
              <h3 className="mb-3 flex items-center gap-2">
                <MapPin className="w-5 h-5 text-[#0066FF]" />
                Gợi ý nhanh
              </h3>
              <p className="text-muted-foreground mb-4">
                Thử các câu hỏi mẫu để bắt đầu lên kế hoạch:
              </p>
              <div className="space-y-2">
                {QUICK_PROMPTS.map((prompt, index) => (
                  <button
                    key={index}
                    onClick={() => handleQuickPrompt(prompt)}
                    className="w-full text-left p-3 rounded-xl border border-border hover:border-[#0066FF] hover:bg-[#0066FF]/5 transition-colors"
                  >
                    <p className="text-foreground/90">{prompt}</p>
                  </button>
                ))}
              </div>
            </div>

            <div className="bg-gradient-to-br from-[#0066FF]/10 to-[#00C29A]/10 rounded-2xl p-4">
              <h4 className="mb-2">💡 Mẹo khi chat</h4>
              <ul className="space-y-2 text-muted-foreground">
                <li className="flex gap-2">
                  <span>•</span>
                  <span>Nói rõ ngân sách và số ngày</span>
                </li>
                <li className="flex gap-2">
                  <span>•</span>
                  <span>Chia sẻ sở thích (chill, phiêu lưu...)</span>
                </li>
                <li className="flex gap-2">
                  <span>•</span>
                  <span>Đề cập thời tiết yêu thích</span>
                </li>
                <li className="flex gap-2">
                  <span>•</span>
                  <span>Nói về ẩm thực quan tâm</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Itinerary Panel */}
      {showItinerary && (
        <div className="lg:w-1/2 xl:w-2/5 bg-white overflow-y-auto">
          <ItineraryPanel onClose={() => setShowItinerary(false)} />
        </div>
      )}
    </div>
  );
}
