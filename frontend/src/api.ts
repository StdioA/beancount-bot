// API服务模块
import type { Message, ErrorMessage } from './types.ts';

// API端点常量
const API_ENDPOINTS = {
  MESSAGES: '/api/messages',
  CHAT: '/api/chat',
  SUBMIT: '/api/submit',
  CLONE: '/api/clone',
  FAVORITE: '/api/favorite'
};

// 错误处理函数
const handleApiError = async (response: Response): Promise<ErrorMessage> => {
  try {
    return await response.json();
  } catch (error) {
    return { error: `API错误: ${response.status} ${response.statusText} ${error}` };
  }
};

// 获取消息列表
export async function fetchMessages(): Promise<{ messages: Message[], favorites: Message[] }> {
  const response = await fetch(API_ENDPOINTS.MESSAGES);
  if (!response.ok) {
    const errorData = await handleApiError(response);
    throw new Error(errorData.error || `获取消息失败: ${response.status} ${response.statusText}`);
  }
  return await response.json();
}

// 发送新消息
export async function sendChatMessage(message: string): Promise<Message> {
  const response = await fetch(API_ENDPOINTS.CHAT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message })
  });
  
  if (!response.ok) {
    const errorData = await handleApiError(response);
    throw new Error(errorData.error || `发送消息失败: ${response.status} ${response.statusText}`);
  }
  
  return await response.json();
}

// 提交交易
export async function submitTransaction(id: number): Promise<void> {
  await handleTransactionRequest(API_ENDPOINTS.SUBMIT, id);
}

// 克隆交易
export async function cloneTransaction(id: number): Promise<void> {
  await handleTransactionRequest(API_ENDPOINTS.CLONE, id);
}

// 切换收藏状态
export async function toggleFavoriteStatus(id: number, favorite: boolean): Promise<void> {
  const response = await fetch(API_ENDPOINTS.FAVORITE, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id, favorite })
  });
  
  if (!response.ok) {
    const errorData = await handleApiError(response);
    throw new Error(errorData.error || `切换收藏状态失败: ${response.status} ${response.statusText}`);
  }
}

// 处理交易请求的通用函数
async function handleTransactionRequest(endpoint: string, id: number): Promise<void> {
  const response = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id })
  });
  
  if (!response.ok) {
    const errorData = await handleApiError(response);
    throw new Error(errorData.error || `交易操作失败: ${response.status} ${response.statusText}`);
  }
}