// UI组件模块
import type { Message, ElementConfig, MessageStatus } from './types.ts';
import {
  messageStorage, messageHistory, submitTransactionButton, transactionText, cloneTransactionButton,
  messageFavorites, transactionDialog, errorDialog, slidingElements,
  amountDisplay,
  modifyAmountButton,
  numpadContainer,
  submitWithAmountButton,
} from './storage.js';
import { toggleFavoriteStatus, deleteMessage } from './api.js';
import { buildIconDom, faTrash, faCheck, faStar } from './icons.js';

// 样式配置
const STYLES = {
  messageContainer: (status: MessageStatus) => [
    'flex', 'container', 'max-w-4xl', 'justify-between', 'items-center', 'p-2', 
    'bg-white', 'rounded-lg', 'shadow-sm', 'relative', 'overflow-hidden', 'message',
    status === 'submitted' ? 'bg-green-200' : 'bg-gray-200'
  ],
  textDiv: ['justify-stretch', 'font-medium', 'text-gray-800'],
  rightContainer: ['flex', 'items-center', 'right-container'],
  collectIcon: (isFavorite: boolean) => [
    'justify-end', 'p-2', 'text-gray-400',
    isFavorite ? 'text-yellow-500' : 'hover:text-yellow-500',
    'hover:scale-120', 'transition', 'duration-20',
    'ele-collect'
  ],
  submittedIcon: ['justify-end', 'p-2', 'text-green-500', 'font-bold', 'ele-check'],
  deleteButton: ['absolute', 'right-0', 'top-0', 'bottom-0', 'bg-red-500', 'text-white', 'flex', 'items-center', 'justify-center',
                 'w-10', 'px-4', 'transform', 'translate-x-full', 'transition-transform', 'duration-300', 'ease-out', 'ele-delete']
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
  const element = createElement<HTMLDivElement>('div', {
    classes: STYLES.submittedIcon,
    attrs: { 'aria-label': 'Submitted' }
  });
  element.appendChild(buildIconDom(faCheck));
  return element;
}

// 构建收藏按钮元素
export function buildCollectElement(msg: Message, onClick: EventListener): HTMLElement {
  const element = createElement<HTMLDivElement>('div', {
    classes: STYLES.collectIcon(msg.favorite),
    events: { click: (e) => {
      e.stopPropagation();
      onClick(e);
    }}
  });
  element.appendChild(buildIconDom(faStar));
  return element;
}

function createDeleteButton(messageDiv: HTMLElement): HTMLElement {
  const id = Number(messageDiv.dataset.msgId!);
  const button = createElement<HTMLDivElement>('div', {
    classes: STYLES.deleteButton,
    events: { click: async (e) => {
      e.stopPropagation();
      try {
        // 添加左滑消失动画
        messageDiv.style.transition = 'transform 0.3s ease-out, opacity 0.3s ease-out';
        messageDiv.style.transform = 'translateX(-100%)';
        messageDiv.style.opacity = '0';
        
        // 等待动画完成后再删除元素
        setTimeout(async () => {
          await deleteMessage(id);
          document.querySelectorAll(`.message[data-msg-id="${id}"]`)?.forEach(el => el.remove());
        }, 300);
      } catch (error) {
        console.error('Error deleting message:', error);
        await showErrorDialog(errorDialog, error.message || '删除消息失败。请查看控制台获取详细信息。');
      }
    }}
  });
  // 使用导入的 faTrash 图标创建元素
  button.appendChild(buildIconDom(faTrash));
  return button;
}

function clearSlidingElements() {
  slidingElements.forEach(el => {
    el.style.transform = 'translateX(0)';
    el.querySelector<HTMLElement>('.ele-delete').style.transform = 'translateX(100%)';
  });
  slidingElements.clear();
}

export function buildMessageElement(msg: Message): HTMLElement {
  const { id, message: msgText, status: msgStatus } = msg;

  // 构建消息主体
  const messageDiv = createElement<HTMLDivElement>('div', {
    classes: STYLES.messageContainer(msgStatus),
    attrs: { 'data-msg-id': id.toString() },
    events: { click: (e) => {
      showTransactionDialog(id);
      // 将所有划过去的元素复位
      clearSlidingElements();
      e.stopPropagation();
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
  
  // 添加删除按钮
  const deleteButton = createDeleteButton(messageDiv);
  messageDiv.appendChild(deleteButton);
  
  // 添加左滑手势
  let startX = 0;
  let currentX = 0;
  let isDragging = false;
  let draggingStartTime = 0;
  const dragThreshold = 100;
  
  const handleTouchStart = (e: TouchEvent) => {
    startX = e.touches[0].clientX;
    isDragging = true;
    draggingStartTime = Date.now();
  };
  
  const handleTouchMove = (e: TouchEvent) => {
    if (!isDragging) return;
    if (Date.now() - draggingStartTime < dragThreshold) return; // 忽略短时间内的滑动，防止误触
    currentX = e.touches[0].clientX;
    const diffX = startX - currentX;
    
    // 只允许左滑
    if (diffX > 0) {
      // 限制最大滑动距离为删除按钮宽度
      const translateX = Math.min(diffX, 80);
      messageDiv.style.transform = `translateX(-${translateX}px)`;
      deleteButton.style.transform = `translateX(calc(100% - ${translateX}px))`;
    }
  };
  
  const handleTouchEnd = () => {
    if (!isDragging) return;
    if (Date.now() - draggingStartTime < dragThreshold) return; // 忽略短时间内的滑动，防止误触

    isDragging = false;
    
    const diffX = startX - currentX;
    
    // 如果滑动距离超过阈值，显示删除按钮
    if (diffX > 40) {
      clearSlidingElements(); // 将其他元素复位
      messageDiv.style.transform = 'translateX(-80px)';
      deleteButton.style.transform = 'translateX(calc(100% - 80px))';
      slidingElements.add(messageDiv);
    } else {
      // 否则恢复原位
      messageDiv.style.transform = 'translateX(0)';
      deleteButton.style.transform = 'translateX(100%)';
      slidingElements.delete(messageDiv);
    }
  };
  
  // 点击其他区域时恢复原位
  document.addEventListener('click', (e) => {
    if (!messageDiv.contains(e.target as Node)) {
      messageDiv.style.transform = 'translateX(0)';
      deleteButton.style.transform = 'translateX(100%)';
      slidingElements.delete(messageDiv);
    }
  });
  
  messageDiv.addEventListener('touchstart', handleTouchStart);
  messageDiv.addEventListener('touchmove', handleTouchMove);
  messageDiv.addEventListener('touchend', handleTouchEnd);
  
  return messageDiv;
}

// 添加消息到列表
export async function appendMessage(listElement: HTMLElement, msg: Message): Promise<HTMLElement> {
  const { id } = msg;
  messageStorage.set(id, msg);

  const messageDiv = buildMessageElement(msg);

  listElement.firstElementChild.appendChild(messageDiv);
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
  modifyAmountButton.classList.toggle('hidden', false);
  submitWithAmountButton.classList.toggle('hidden', true);
  numpadContainer.classList.add('hidden');
  transactionDialog.classList.remove('hidden');

  // 重置数字键盘显示
  resetAmountDisplay();

  [messageHistory, messageFavorites].forEach((list: HTMLElement) => {
    list.scrollTop = list.scrollHeight;
  });
}

// 隐藏交易对话框
export function hideTransactionDialog(): void {
  transactionDialog.classList.add('hidden');
  numpadContainer.classList.add('hidden');
  modifyAmountButton.classList.remove('hidden');
  submitWithAmountButton.classList.add('hidden');
}

// 提取交易金额
export function extractAmount(text: string): string | null {
  // 匹配交易文本中的金额，假设金额是第一个数字
  const match = text.match(/^\s*(\d+(\.\d+)?)\s/);
  return match ? match[1] : null;
}

// 重置金额显示
export function resetAmountDisplay(): void {
  const msgId = transactionText.dataset.msgId;
  if (!msgId) return;
  
  const message = messageStorage.get(Number(msgId));
  if (!message) return;
  
  const amount = extractAmount(message.message);
  amountDisplay.textContent = amount || '';
  amountDisplay.dataset.originalAmount = amount || '';
}

// 显示数字键盘
export function showNumpad(): void {
  numpadContainer.classList.remove('hidden');
  modifyAmountButton.classList.add('hidden');
  submitWithAmountButton.classList.remove('hidden');
  
  // 确保金额显示已初始化
  if (!amountDisplay.textContent) {
    resetAmountDisplay();
  }
}

// 隐藏数字键盘
export function hideNumpad(): void {
  numpadContainer.classList.add('hidden');
  modifyAmountButton.classList.remove('hidden');
  submitWithAmountButton.classList.add('hidden');
}

// 处理数字键盘输入
export function handleNumpadInput(value: string): void {
  // 如果是第一次点击，清空显示
  if (amountDisplay.textContent === amountDisplay.dataset.originalAmount) {
    amountDisplay.textContent = '';
  }
  
  // 处理小数点
  if (value === '.' && amountDisplay.textContent.includes('.')) {
    return; // 已经有小数点了，忽略
  }
  
  // 添加数字或小数点
  amountDisplay.textContent += value;
}

// 清除金额显示
export function clearAmountDisplay(): void {
  amountDisplay.textContent = '';
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
      // 清空现有内容并添加图标
      // messageElement.innerHTML = '';
      // messageElement.appendChild(buildIconDom(faStar));
    });
  } catch (error) {
    console.error('Error toggling favorite:', error);
    await showErrorDialog(errorDialog, error.message || 'Toggle favorite failed. Please check console for details.');
  }
}