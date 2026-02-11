import { motion } from 'motion/react';
import { User, Sparkles } from 'lucide-react';

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  itineraryData?: ItineraryData;
}

export interface Activity {
  id: string;
  name: string;
  icon: string;
  time: string;
  duration: string;
  rating?: number | null;
  address?: string | null;
  cost?: string | null;
  travelTime?: string | null;
}

export interface DayItinerary {
  day: number;
  date: string;
  activities: Activity[];
}

export interface HotelInfo {
  name: string;
  price: string;
  rating?: number | null;
  image?: string;
}

export interface ItineraryData {
  destination: string;
  duration: string;
  budget: string;
  days: DayItinerary[];
  hotel?: HotelInfo;
}

interface ChatMessageProps {
  message: Message;
  onSaveItinerary?: (data: ItineraryData) => void;
}

export function ChatMessage({ message, onSaveItinerary }: ChatMessageProps) {
  const isUser = message.role === 'user';

  // Check if content contains HTML tags (for assistant messages only)
  const hasHTML =
    !isUser &&
    (message.content.includes('<b>') ||
      message.content.includes('</b>') ||
      message.content.includes('<strong>') ||
      message.content.includes('</strong>'));

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={`flex gap-4 mb-6 ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      {!isUser && (
        <div className='flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-primary to-secondary flex items-center justify-center shadow-md'>
          <Sparkles className='h-4 w-4 text-white' />
        </div>
      )}

      <div className={`max-w-[75%] ${isUser ? 'order-first' : ''}`}>
        {/* Message Bubble */}
        <div
          className={`rounded-2xl px-5 py-3 shadow-sm transition-all duration-200 ${
            isUser
              ? 'bg-[#EDF2FF] dark:bg-[#1e3a8a] text-foreground ml-auto border border-transparent dark:border-primary/50'
              : 'bg-white dark:bg-card text-foreground border border-border'
          }`}
        >
          {hasHTML ? (
            <div
              className='whitespace-pre-wrap break-words'
              dangerouslySetInnerHTML={{
                __html: message.content.replace(/\n/g, '<br />'),
              }}
            />
          ) : (
            <p className='whitespace-pre-wrap break-words'>{message.content}</p>
          )}
        </div>

        {/* Timestamp */}
        <div
          className={`text-muted-foreground mt-1 px-2 text-[13px] ${
            isUser ? 'text-right' : 'text-left'
          }`}
        >
          {message.timestamp}
        </div>
      </div>

      {isUser && (
        <div className='flex-shrink-0 w-8 h-8 rounded-full bg-muted dark:bg-muted flex items-center justify-center'>
          <User className='h-4 w-4 text-muted-foreground' />
        </div>
      )}
    </motion.div>
  );
}

// Typing Indicator Component
export function TypingIndicator() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className='flex gap-4 mb-6'
    >
      <div className='flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-primary to-secondary flex items-center justify-center shadow-md'>
        <Sparkles className='h-4 w-4 text-white' />
      </div>
      <div className='bg-white dark:bg-card rounded-2xl px-5 py-3 shadow-sm border border-border'>
        <div className='flex items-center gap-2'>
          <span className='text-muted-foreground'>TravelGPT đang viết</span>
          <div className='flex gap-1'>
            <motion.div
              animate={{ scale: [1, 1.2, 1] }}
              transition={{ repeat: Infinity, duration: 0.6, delay: 0 }}
              className='w-1.5 h-1.5 bg-primary rounded-full'
            />
            <motion.div
              animate={{ scale: [1, 1.2, 1] }}
              transition={{ repeat: Infinity, duration: 0.6, delay: 0.2 }}
              className='w-1.5 h-1.5 bg-primary rounded-full'
            />
            <motion.div
              animate={{ scale: [1, 1.2, 1] }}
              transition={{ repeat: Infinity, duration: 0.6, delay: 0.4 }}
              className='w-1.5 h-1.5 bg-primary rounded-full'
            />
          </div>
        </div>
      </div>
    </motion.div>
  );
}
