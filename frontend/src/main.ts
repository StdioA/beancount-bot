import './style.css';
import { registerSW } from 'virtual:pwa-register';
import { initLocale } from './i18n.js';

// 常量定义
const API_MESSAGES = '/api/messages';
const API_CHAT = '/api/chat';
const API_SUBMIT = '/api/submit';
const API_CLONE = '/api/clone';
const API_FAVORITE = '/api/favorite';

// DOM 元素获取 (添加类型断言和判空)
const messageHistory = document.getElementById('message-history') as HTMLElement;
const messageFavorites = document.getElementById('message-favorites') as HTMLElement;
const messageInput = document.getElementById('message-input') as HTMLInputElement;
const sendButton = document.getElementById('send-button') as HTMLButtonElement;
const transactionDialog = document.getElementById('transaction-dialog') as HTMLElement;
const transactionText = document.getElementById('transaction-text') as HTMLElement;
const submitTransactionButton = document.getElementById('submit-transaction') as HTMLButtonElement;
const cloneTransactionButton = document.getElementById('clone-transaction') as HTMLButtonElement;
const closeDialogButton = document.getElementById('close-dialog') as HTMLButtonElement;
const errorDialog = document.getElementById('error-dialog') as HTMLElement;
const loadingIndicator = document.getElementById('loading-indicator') as HTMLElement;

const notFavoriteStar = "☆";
const favoriteStar = "★";

type MessageStatus = 'submitted' | 'pending';
interface Message {
  id: number;
  message: string;
  transaction_text: string;
  status: MessageStatus;
  favorite: boolean;
}

interface ErrorMessage {
  error: string;
}

// 全局消息存储
const messageStorage: Map<number, Message> = new Map();

async function fetchMessages(): Promise<void> {
  try {
    const response: Response = await fetch(API_MESSAGES);
    if (!response.ok) {
      const message = `Failed to fetch messages: ${response.status} ${response.statusText}`;
      console.error(message);
      await popupError(message);
      return;
    }
    const { messages, favorites }: { messages: Message[], favorites: Message[] } = await response.json();
    messages.forEach(msg => {
      appendMessage(messageHistory, msg);
    });
    favorites.forEach(msg => {
      appendMessage(messageFavorites, msg);
    });
  } catch (error) {
    console.error('Error fetching messages:', error);
    await popupError('Failed to fetch messages. Please check console for details.');
  }
}

async function sendMessage() {
  const message = messageInput.value;
  if (message === '') {
    return;
  }

  sendButton.disabled = true;
  try {
    const response: Response = await fetch(API_CHAT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ message })
    });
    if (!response.ok) {
      const errorData: ErrorMessage = await response.json();
      const errorMessage = errorData.error || `Send message failed: ${response.status} ${response.statusText}`;
      console.error('Send message failed:', errorMessage, errorData);
      throw new Error(errorMessage);
    }
    const data: Message = await response.json();
    messageInput.value = '';
    appendMessage(messageHistory, data);
    showTransactionDialog(data.id);
  } catch (error) {
    console.error('Error sending message:', error);
    await popupError(error.message || 'Failed to send message. Please check console for details.');
  } finally {
    sendButton.disabled = false;
  }
}

async function handleTransactionAction(apiEndpoint: string, msgId: string, button: HTMLButtonElement): Promise<void> {
  button.disabled = true;
  try {
    const response = await fetch(apiEndpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ id: Number(msgId) })
    });
    if (!response.ok) {
      const errorData: ErrorMessage = await response.json();
      const errorMessage = errorData.error || `Transaction action failed: ${response.status} ${response.statusText}`;
      console.error(`Transaction action (${apiEndpoint}) failed:`, errorMessage, errorData);
      throw new Error(errorMessage);
    }
    // Find the message element and update its status
    const messageElements = document.querySelectorAll<HTMLDivElement>(`[data-msg-id="${msgId}"]>div:last-child`);
    messageElements.forEach((ele: HTMLDivElement) => {
      if (ele.querySelector('.ele-check') === null) {
        ele.insertBefore(buildSubmittedElement(), ele.firstChild);
      }
    })
    await markButtonSuccess(button);
  } catch (error) {
    console.error(`Error during transaction action (${apiEndpoint}):`, error);
    await popupError(error.message || `Transaction action failed. Please check console for details.`);
  } finally {
    button.disabled = false;
  }
}

async function toggleFavorite(msgId: string): Promise<void> {
  try {
    const message = messageStorage.get(Number(msgId));
    const targetFavorite = !messageStorage.get(Number(msgId))?.favorite;
    const response = await fetch(API_FAVORITE, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        id: Number(msgId),
        favorite: targetFavorite,
      })
    });
    if (!response.ok) {
      const errorData: ErrorMessage = await response.json();
      const errorMessage = errorData.error || `Toggle favorite failed: ${response.status} ${response.statusText}`;
      console.error('Toggle favorite failed:', errorMessage, errorData);
      throw new Error(errorMessage);
    }
    message.favorite = targetFavorite;

    const messageElements = document.querySelectorAll<HTMLDivElement>(`[data-msg-id="${msgId}"] div.ele-collect`);
    messageElements.forEach(messageElement => {
      messageElement.classList.toggle("text-yellow-500");
      messageElement.classList.toggle("hover:text-yellow-500");
      messageElement.innerText = targetFavorite ? favoriteStar: notFavoriteStar;
    });
  } catch (error) {
    console.error('Error toggling favorite:', error);
    await popupError(error.message || 'Toggle favorite failed. Please check console for details.');
  }
}

// 通用元素构建工具函数
type ElementConfig = {
  classes?: string[];
  attrs?: Record<string, string>;
  events?: Record<string, EventListener>;
};

function createElement<T extends HTMLElement>(
  tag: string,
  { classes = [], attrs = {}, events = {} }: ElementConfig = {}
): T {
  const el = document.createElement(tag) as T;
  el.classList.add(...classes.filter(Boolean));
  Object.entries(attrs).forEach(([key, value]) => el.setAttribute(key, value));
  Object.entries(events).forEach(([type, handler]) => el.addEventListener(type, handler));
  return el;
}

// 样式配置

const STYLES = {
  messageContainer: (status: MessageStatus) => [
    'flex', 'container', 'justify-between', 'items-center', 'p-2', 
    'bg-white', 'rounded-lg', 'shadow-sm',
    status === 'submitted' ? 'bg-green-200' : 'bg-gray-200'
  ],
  textDiv: ['justify-stretch', 'font-medium', 'text-gray-800'],
  rightContainer: ['flex', 'items-center'],
  collectIcon: (isFavorite: boolean) => [
    'justify-end', 'p-2', 'text-gray-400',
    isFavorite ? 'text-yellow-500' : 'hover:text-yellow-500',
    'ele-collect'
  ],
  submittedIcon: ['justify-end', 'p-2', 'text-green-500', 'font-bold', 'ele-check']
};

// 模板组件
function buildSubmittedElement(): HTMLElement {
  return createElement<HTMLDivElement>('div', {
    classes: STYLES.submittedIcon,
    attrs: { 'aria-label': 'Submitted' }
  }).appendChild(document.createTextNode('✓')).parentElement!;
}

function buildCollectElement(msg: Message, onClick: EventListener): HTMLElement {
  return createElement<HTMLDivElement>('div', {
    classes: STYLES.collectIcon(msg.favorite),
    events: { click: (e) => {
      e.stopPropagation();
      onClick(e);
    }}
  }).appendChild(document.createTextNode(msg.favorite ? favoriteStar : notFavoriteStar)).parentElement!;
}

// 重构后的主函数
function appendMessage(listElement: HTMLElement, msg: Message): HTMLElement {
  const { id, message: msgText, transaction_text: txText, status: msgStatus } = msg;
  messageStorage.set(id, msg);

  // 构建消息主体
  const messageDiv = createElement<HTMLDivElement>('div', {
    classes: STYLES.messageContainer(msgStatus),
    attrs: { 'data-msg-id': id.toString() }
  });

  // 文本内容区域
  const textDiv = createElement<HTMLDivElement>('div', {
    classes: STYLES.textDiv
  });
  textDiv.textContent = msgText;

  // 右侧操作区域
  const rightDiv = createElement<HTMLDivElement>('div', {
    classes: STYLES.rightContainer
  });

  // 收藏按钮
  const collectDiv = buildCollectElement(msg, () => toggleFavorite(id.toString()));

  // 条件元素
  if (msgStatus === 'submitted') {
    rightDiv.appendChild(buildSubmittedElement());
  }
  rightDiv.appendChild(collectDiv);
  messageDiv.append(textDiv, rightDiv);

  // 交易文本交互
  if (txText) {
    messageDiv.addEventListener('click', (e) => {
      e.stopPropagation();
      showTransactionDialog(id);
    });
  }

  // 插入列表并滚动
  listElement.appendChild(messageDiv);
  listElement.scrollTop = listElement.scrollHeight;

  return messageDiv;
}
function showTransactionDialog(msgId: number): void {
  const { transaction_text: txText, status: msgStatus } = messageStorage.get(msgId)!;

  transactionText.textContent = txText;
  transactionText.dataset.msgId = msgId.toString();

  const isSubmitted = msgStatus === 'submitted';
  submitTransactionButton.classList.toggle('hidden', isSubmitted);
  cloneTransactionButton.classList.toggle('hidden', !isSubmitted);
  transactionDialog.classList.remove('hidden');
}

async function markButtonSuccess(button: HTMLButtonElement): Promise<void> {
  const originalButtonText = button.textContent ?? '';

  button.disabled = true;
  button.classList.remove('bg-blue-500', 'hover:bg-blue-700');
  button.classList.add('bg-green-500');
  button.textContent = 'Done!';
  await new Promise(resolve => setTimeout(resolve, 1000));

  button.disabled = false;
  button.classList.remove('bg-green-500');
  button.classList.add('bg-blue-500', 'hover:bg-blue-700');
  button.textContent = originalButtonText;
}

async function popupError(message: string): Promise<void> {
  errorDialog.textContent = message;
  errorDialog.classList.remove('hidden');
  await new Promise(resolve => setTimeout(resolve, 3000));
  errorDialog.classList.add('hidden');
}

// Service worker 定时检查 & 刷新提示
const intervalMS = 60 * 60 * 1000;
const updateSW = registerSW({
  onRegistered: (r) => {
    if (r) {
      setInterval(() => {
        r.update();
      }, intervalMS);
    }
  },
  onNeedRefresh: () => {
    // 显示更新提示框
    if (window.confirm(`There is a new version of this app available. Do you want to update?`)) {
      updateSW();
    }
  },
  onOfflineReady: () => {
    // 显示离线提示
    popupError('This app is offline.');
  }
});

function switchTab(tab: string): void {
  // 切换选项卡
  document.querySelectorAll('[data-tab]').forEach((el: HTMLElement) => {
      el.classList.toggle('hidden', el.dataset.tab !== tab)
  })
  
  // 更新按钮状态
  document.querySelectorAll('[data-tab-button]').forEach((btn: HTMLButtonElement) => {
      btn.classList.toggle('bg-blue-500', btn.dataset.tabButton === tab)
      btn.classList.toggle('text-white', btn.dataset.tabButton === tab)
      btn.classList.toggle('bg-gray-100', btn.dataset.tabButton !== tab)
  })
}

// Register event linsteners & fetch messages
document.addEventListener('DOMContentLoaded', async () => {
  sendButton.addEventListener('click', sendMessage);
  messageInput.addEventListener('keydown', async (event) => {
    if (event.key === 'Enter') {
      await sendMessage();
    }
  });

  submitTransactionButton.addEventListener('click', async () => {
    const msgId = transactionText.dataset.msgId as string;
    await handleTransactionAction(API_SUBMIT, msgId, submitTransactionButton);
  });
  cloneTransactionButton.addEventListener('click', async () => {
    const msgId = transactionText.dataset.msgId as string;
    await handleTransactionAction(API_CLONE, msgId, cloneTransactionButton);
  });

  closeDialogButton.addEventListener('click', () => {
    transactionDialog.classList.add('hidden');
  });
  document.addEventListener('click', (event: MouseEvent) => {
    if (!transactionDialog.contains(event.target as Node | null) && !((event.target as HTMLElement)?.classList.contains('message'))) {
      transactionDialog.classList.add('hidden');
    }
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      transactionDialog.classList.add('hidden');
    }
  });

  document.querySelectorAll('[data-tab-button]').forEach((btn: HTMLButtonElement) => {
    btn.addEventListener('click', () => {
      switchTab(btn.dataset.tabButton);
    });
  });

  loadingIndicator.classList.replace('hidden', 'flex');
  await Promise.all([initLocale(), fetchMessages()]);
  loadingIndicator.classList.replace('flex', 'hidden');
});
