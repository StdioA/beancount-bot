// UI组件模块
import type { Message, ElementConfig, MessageStatus } from './types.ts';
import {
  messageStorage, messageHistory, submitTransactionButton, transactionText, cloneTransactionButton,
  messageFavorites, transactionDialog, errorDialog,
} from './storage.js';
import { toggleFavoriteStatus } from './api.js';

// 常量定义
const notFavoriteStar = "☆";
const favoriteStar = "★";

// 样式配置
const STYLES = {
  messageContainer: (status: MessageStatus) => [
    'flex', 'container', 'max-w-4xl', 'justify-between', 'items-center', 'p-2', 
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

// 通用元素构建工具函数
export function createElement<T extends HTMLElement>(
  tag: string,
  { classes = [], attrs = {}, events = {} }: ElementConfig = {}
): T {
  const el = document.createElement(tag) as T;
  el.classList.add(...classes.filter(Boolean));
  Object.entries(attrs).forEach(([key, value]) => el.setAttribute(key, value));
  Object.entries(events).forEach(([type, handler]) => el.addEventListener(type, handler));
  return el;
}

// 构建已提交标记元素
export function buildSubmittedElement(): HTMLElement {
  return createElement<HTMLDivElement>('div', {
    classes: STYLES.submittedIcon,
    attrs: { 'aria-label': 'Submitted' }
  }).appendChild(document.createTextNode('✓')).parentElement!;
}

// 构建收藏按钮元素
export function buildCollectElement(msg: Message, onClick: EventListener): HTMLElement {
  return createElement<HTMLDivElement>('div', {
    classes: STYLES.collectIcon(msg.favorite),
    events: { click: (e) => {
      e.stopPropagation();
      onClick(e);
    }}
  }).appendChild(document.createTextNode(msg.favorite ? favoriteStar : notFavoriteStar)).parentElement!;
}

export function buildMessageElement(msg: Message): HTMLElement {
  const { id, message: msgText, status: msgStatus } = msg;

  // 构建消息主体
  const messageDiv = createElement<HTMLDivElement>('div', {
    classes: STYLES.messageContainer(msgStatus),
    attrs: { 'data-msg-id': id.toString() },
    events: { click: (e) => {
      e.stopPropagation();
      showTransactionDialog(id);
    }}
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
  const collectDiv = buildCollectElement(msg, () => handleToggleFavorite(id.toString()));

  // 条件元素
  if (msgStatus === 'submitted') {
    rightDiv.appendChild(buildSubmittedElement());
  }
  rightDiv.appendChild(collectDiv);
  messageDiv.append(textDiv, rightDiv);
  return messageDiv;
}

// 添加消息到列表
export function appendMessage(listElement: HTMLElement, msg: Message): HTMLElement {
  const { id } = msg;
  messageStorage.set(id, msg);

  const messageDiv = buildMessageElement(msg);

  // 插入列表并滚动
  listElement.firstElementChild.appendChild(messageDiv);
  listElement.scrollTop = listElement.scrollHeight;

  return messageDiv;
}

// 显示错误提示
export async function showErrorDialog(errorDialog: HTMLElement, message: string): Promise<void> {
  errorDialog.textContent = message;
  errorDialog.classList.remove('hidden');
  await new Promise(resolve => setTimeout(resolve, 3000));
  errorDialog.classList.add('hidden');
}

// 切换标签页
export function switchTab(tab: string): void {
  // 切换选项卡
  document.querySelectorAll<HTMLDivElement>('[data-tab]').forEach(el => {
    el.classList.toggle('hidden', el.dataset.tab !== tab);
  });
  
  // 更新按钮状态
  document.querySelectorAll<HTMLButtonElement>('[data-tab-button]').forEach(btn => {
    btn.classList.toggle('bg-blue-500', btn.dataset.tabButton === tab);
    btn.classList.toggle('text-white', btn.dataset.tabButton === tab);
    btn.classList.toggle('bg-gray-100', btn.dataset.tabButton !== tab);
  });
}

// 标记按钮操作成功
export async function markButtonSuccess(button: HTMLButtonElement): Promise<void> {
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

// 显示交易对话框
export function showTransactionDialog(msgId: number): void {
  const message = messageStorage.get(msgId);
  if (!message) return;
  
  const { transaction_text: txText, status: msgStatus } = message;

  transactionText.textContent = txText;
  transactionText.dataset.msgId = msgId.toString();

  const isSubmitted = msgStatus === 'submitted';
  submitTransactionButton.classList.toggle('hidden', isSubmitted);
  cloneTransactionButton.classList.toggle('hidden', !isSubmitted);
  transactionDialog.classList.remove('hidden');

  [messageHistory, messageFavorites].forEach((list: HTMLElement) => {
    list.scrollTop = list.scrollHeight;
  });
}

// 隐藏交易对话框
export function hideTransactionDialog(): void {
  transactionDialog.classList.add('hidden');
}

// 切换收藏状态
export async function handleToggleFavorite(msgId: string): Promise<void> {
  try {
    const message = messageStorage.get(Number(msgId));
    if (!message) return;
    
    const targetFavorite = !message.favorite;
    await toggleFavoriteStatus(Number(msgId), targetFavorite);
    message.favorite = targetFavorite;

    const messageElements = document.querySelectorAll<HTMLDivElement>(`[data-msg-id="${msgId}"] div.ele-collect`);
    messageElements.forEach(messageElement => {
      messageElement.classList.toggle("text-yellow-500", targetFavorite);
      messageElement.classList.toggle("hover:text-yellow-500", !targetFavorite);
      messageElement.innerText = targetFavorite ? favoriteStar: notFavoriteStar;
    });
  } catch (error) {
    console.error('Error toggling favorite:', error);
    await showErrorDialog(errorDialog, error.message || 'Toggle favorite failed. Please check console for details.');
  }
}