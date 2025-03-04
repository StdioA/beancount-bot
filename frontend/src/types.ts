// 类型定义
export type MessageStatus = 'submitted' | 'pending';

export interface Message {
  id: number;
  message: string;
  transaction_text: string;
  status: MessageStatus;
  favorite: boolean;
}

export interface ErrorMessage {
  error: string;
}

export type ElementConfig = {
  classes?: string[];
  attrs?: Record<string, string>;
  events?: Record<string, EventListener>;
};