import { useState } from 'react';
import {
  Plus,
  MessageCircle,
  Edit2,
  Trash2,
  Menu,
  X,
  User,
  BookMarked,
  LogOut,
} from 'lucide-react';
import { Button } from './ui/button';
import { ScrollArea } from './ui/scroll-area';
import { motion, AnimatePresence } from 'motion/react';

export interface Conversation {
  id: string;
  title: string;
  date: string;
  preview?: string;
}

interface ConversationSidebarProps {
  conversations: Conversation[];
  activeConversationId: string | null;
  onSelectConversation: (id: string) => void;
  onNewConversation: () => void;
  onRenameConversation: (id: string, newTitle: string) => void;
  onDeleteConversation: (id: string) => void;
  isMobileOpen?: boolean;
  onMobileClose?: () => void;
  onNavigate?: (page: 'profile' | 'itineraries') => void;
  onLogout?: () => void;
}

export function ConversationSidebar({
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewConversation,
  onRenameConversation,
  onDeleteConversation,
  isMobileOpen = false,
  onMobileClose,
  onNavigate,
  onLogout,
}: ConversationSidebarProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  const handleStartEdit = (conversation: Conversation) => {
    setEditingId(conversation.id);
    setEditValue(conversation.title);
  };

  const handleSaveEdit = (id: string) => {
    if (editValue.trim()) {
      onRenameConversation(id, editValue.trim());
    }
    setEditingId(null);
  };

  const handleConversationClick = (id: string) => {
    onSelectConversation(id);
    if (onMobileClose) {
      onMobileClose();
    }
  };

  const sidebarContent = (
    <div className='flex flex-col h-full bg-white dark:bg-card border-r border-border'>
      {/* Header with Title and New Chat Button */}
      <div className='p-4 border-b border-border flex-shrink-0 space-y-3'>
        <h1 className='text-lg font-semibold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent text-center'>
          Travel Planner Chatbot
        </h1>
        <Button
          onClick={onNewConversation}
          className='w-full bg-primary hover:bg-primary/90 text-white rounded-xl transition-all duration-200 hover:shadow-md'
        >
          <Plus className='mr-2 h-4 w-4' />
          Cuộc trò chuyện mới
        </Button>
      </div>

      {/* Conversations List */}
      <ScrollArea className='flex-1 h-0'>
        <div className='p-3 space-y-2'>
          <AnimatePresence>
            {conversations.map((conversation) => (
              <motion.div
                key={conversation.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.2 }}
                onMouseEnter={() => setHoveredId(conversation.id)}
                onMouseLeave={() => setHoveredId(null)}
                className={`group relative rounded-xl p-3 cursor-pointer transition-all duration-200 ${
                  activeConversationId === conversation.id
                    ? 'bg-primary/10 dark:bg-primary/20 border border-primary/20 dark:border-primary/30 shadow-sm'
                    : 'bg-white dark:bg-card hover:bg-muted dark:hover:bg-muted border border-transparent'
                }`}
                onClick={() => handleConversationClick(conversation.id)}
              >
                <div className='flex items-start gap-3'>
                  <div
                    className={`mt-1 transition-colors duration-200 ${
                      activeConversationId === conversation.id
                        ? 'text-primary'
                        : 'text-muted-foreground'
                    }`}
                  >
                    <MessageCircle className='h-4 w-4' />
                  </div>
                  <div className='flex-1 min-w-0'>
                    {editingId === conversation.id ? (
                      <input
                        type='text'
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        onBlur={() => handleSaveEdit(conversation.id)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter')
                            handleSaveEdit(conversation.id);
                          if (e.key === 'Escape') setEditingId(null);
                        }}
                        className='w-full px-2 py-1 rounded border border-primary dark:border-primary bg-white dark:bg-card dark:text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20'
                        autoFocus
                        onClick={(e) => e.stopPropagation()}
                      />
                    ) : (
                      <>
                        <div className='truncate'>{conversation.title}</div>
                        <div className='text-muted-foreground mt-1 text-[13px]'>
                          {conversation.date}
                        </div>
                      </>
                    )}
                  </div>
                </div>

                {/* Action Buttons */}
                {hoveredId === conversation.id &&
                  editingId !== conversation.id && (
                    <div className='absolute right-2 top-3 flex gap-1 bg-white dark:bg-card rounded-lg shadow-md p-1'>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleStartEdit(conversation);
                        }}
                        className='p-1.5 hover:bg-muted rounded transition-colors'
                        title='Đổi tên'
                      >
                        <Edit2 className='h-3.5 w-3.5 text-muted-foreground' />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          if (
                            confirm('Bạn có chắc muốn xóa cuộc trò chuyện này?')
                          ) {
                            onDeleteConversation(conversation.id);
                          }
                        }}
                        className='p-1.5 hover:bg-destructive/10 rounded transition-colors'
                        title='Xóa'
                      >
                        <Trash2 className='h-3.5 w-3.5 text-destructive' />
                      </button>
                    </div>
                  )}
              </motion.div>
            ))}
          </AnimatePresence>

          {conversations.length === 0 && (
            <div className='text-center py-8 text-muted-foreground'>
              <MessageCircle className='h-12 w-12 mx-auto mb-3 opacity-30' />
              <p className='text-sm'>Chưa có cuộc trò chuyện nào</p>
              <p className='text-sm mt-1'>Bắt đầu cuộc trò chuyện mới!</p>
            </div>
          )}
        </div>
      </ScrollArea>

      {/* User Menu at Bottom */}
      <div className='p-3 border-t border-border flex-shrink-0 bg-white dark:bg-card'>
        <div className='space-y-1'>
          <button
            onClick={() => {
              onNavigate?.('profile');
              if (onMobileClose) onMobileClose();
            }}
            className='w-full flex items-center gap-3 px-3 py-2.5 hover:bg-muted rounded-xl transition-colors text-left'
          >
            <User className='h-4 w-4 text-muted-foreground' />
            <span className='text-sm'>Hồ sơ cá nhân</span>
          </button>
          <button
            onClick={() => {
              onNavigate?.('itineraries');
              if (onMobileClose) onMobileClose();
            }}
            className='w-full flex items-center gap-3 px-3 py-2.5 hover:bg-muted rounded-xl transition-colors text-left'
          >
            <BookMarked className='h-4 w-4 text-muted-foreground' />
            <span className='text-sm'>Lịch trình đã lưu</span>
          </button>
          <div className='h-px bg-border my-2' />
          <button
            onClick={() => {
              onLogout?.();
              if (onMobileClose) onMobileClose();
            }}
            className='w-full flex items-center gap-3 px-3 py-2.5 hover:bg-destructive/10 rounded-xl transition-colors text-left text-destructive'
          >
            <LogOut className='h-4 w-4' />
            <span className='text-sm'>Đăng xuất</span>
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* Mobile version with overlay */}
      <AnimatePresence>
        {isMobileOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className='fixed inset-0 bg-black/50 z-40 md:hidden'
              onClick={onMobileClose}
            />
            {/* Sidebar */}
            <motion.div
              initial={{ x: '-100%' }}
              animate={{ x: 0 }}
              exit={{ x: '-100%' }}
              transition={{ type: 'spring', damping: 30, stiffness: 300 }}
              className='fixed left-0 top-0 bottom-0 w-[280px] z-50 md:hidden'
            >
              <Button
                variant='ghost'
                size='icon'
                className='absolute right-2 top-2 z-10'
                onClick={onMobileClose}
              >
                <X className='h-5 w-5' />
              </Button>
              {sidebarContent}
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Desktop version - always visible */}
      <div className='hidden md:block w-[280px] h-full'>{sidebarContent}</div>
    </>
  );
}
