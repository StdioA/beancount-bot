// UI组件模块
import type { Message, ElementConfig, MessageStatus } from './types.ts';
import {
  messageStorage, messageHistory, submitTransactionButton, transactionText, cloneTransactionButton,
  messageFavorites, transactionDialog, dialogOverlay, errorDialog, slidingElements,
  amountDisplay,
  modifyAmountButton,
  numpadContainer,
  submitWithAmountButton,
  tabSlider,
} from './storage.js';
import { toggleFavoriteStatus, deleteMessage } from './api.js';
import { buildIconDom, faTrash, faCheck, faStar } from './icons.js';

// 样式配置（浅色默认 + dark: 暗色适配）
const STYLES = {
  messageContainer: (status: MessageStatus) => [
    'flex', 'container', 'max-w-4xl', 'justify-between', 'items-center', 'p-2',
    'bg-white', 'dark:bg-white/5', 'dark:backdrop-blur-xl',
    'rounded-lg', 'shadow-sm', 'relative', 'overflow-hidden', 'message',
    'border', 'border-gray-200', 'dark:border-white/10',
    'border-l-[3px]',
    status === 'submitted' ? 'border-l-emerald-400' : 'border-l-amber-400',
  ],
  textDiv: ['justify-stretch', 'font-medium', 'text-gray-800', 'dark:text-gray-200'],
  rightContainer: ['flex', 'items-center', 'right-container'],
  collectIcon: (isFavorite: boolean) => [
    'justify-end', 'p-2', 'text-gray-400',
    isFavorite ? 'text-yellow-500' : 'hover:text-yellow-500',
    'hover:scale-120', 'transition', 'duration-20',
    'ele-collect'
  ],
  submittedIcon: ['justify-end', 'p-2', 'text-green-500', 'dark:text-emerald-400', 'font-bold', 'ele-check'],
  deleteButton: ['absolute', 'right-0', 'top-0', 'bottom-0', 'bg-red-500', 'dark:bg-red-500/80', 'text-white', 'flex', 'items-center', 'justify-center',
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

// 解析消息文本，突出显示金额
function renderMessageContent(msgText: string): DocumentFragment {
  const fragment = document.createDocumentFragment();
  const amountMatch = msgText.match(/(\d+\.?\d*)\s*(CNY|USD|EUR|JPY|GBP|RMB)/);
  if (amountMatch) {
    const [fullMatch, amount, currency] = amountMatch;
    const before = msgText.slice(0, msgText.indexOf(fullMatch)).trim();
    const after = msgText.slice(msgText.indexOf(fullMatch) + fullMatch.length).trim();

    if (before) {
      const descSpan = createElement<HTMLSpanElement>('span', {
        classes: ['font-light', 'text-gray-600', 'dark:text-gray-300']
      });
      descSpan.textContent = before + ' ';
      fragment.appendChild(descSpan);
    }

    // 金额数字（动画目标）
    const amountSpan = createElement<HTMLSpanElement>('span', {
      classes: ['font-bold', 'text-lg', 'text-gray-900', 'dark:text-white'],
      attrs: { 'data-amount-target': amount }
    });
    amountSpan.textContent = amount;
    fragment.appendChild(amountSpan);

    // 货币单位
    const currencySpan = createElement<HTMLSpanElement>('span', {
      classes: ['font-bold', 'text-lg', 'text-blue-600', 'dark:text-violet-300']
    });
    currencySpan.textContent = ' ' + currency;
    fragment.appendChild(currencySpan);

    if (after) {
      const acctSpan = createElement<HTMLSpanElement>('span', {
        classes: ['font-light', 'text-gray-500', 'dark:text-gray-400', 'text-sm']
      });
      acctSpan.textContent = ' ' + after;
      fragment.appendChild(acctSpan);
    }
  } else {
    const fallbackSpan = createElement<HTMLSpanElement>('span', {
      classes: ['text-gray-800', 'dark:text-gray-200']
    });
    fallbackSpan.textContent = msgText;
    fragment.appendChild(fallbackSpan);
  }
  return fragment;
}

// 金额计数器动画
function animateAmount(element: HTMLElement, targetValue: number, duration: number = 400): void {
  const startTime = performance.now();
  const isDecimal = targetValue % 1 !== 0;
  const decimals = isDecimal ? (targetValue.toString().split('.')[1] || '').length : 0;

  function update(now: number) {
    const elapsed = now - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = targetValue * eased;

    element.textContent = isDecimal
      ? current.toFixed(decimals)
      : Math.round(current).toString();

    if (progress < 1) {
      requestAnimationFrame(update);
    }
  }

  requestAnimationFrame(update);
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
        messageDiv.style.transition = 'transform 0.3s ease-out, opacity 0.3s ease-out';
        messageDiv.style.transform = 'translateX(-100%)';
        messageDiv.style.opacity = '0';

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

  const messageDiv = createElement<HTMLDivElement>('div', {
    classes: STYLES.messageContainer(msgStatus),
    attrs: { 'data-msg-id': id.toString() },
    events: { click: (e) => {
      showTransactionDialog(id);
      clearSlidingElements();
      e.stopPropagation();
    }}
  });

  const textDiv = createElement<HTMLDivElement>('div', {
    classes: STYLES.textDiv
  });
  textDiv.appendChild(renderMessageContent(msgText));

  const rightDiv = createElement<HTMLDivElement>('div', {
    classes: STYLES.rightContainer
  });

  const collectDiv = buildCollectElement(msg, () => handleToggleFavorite(id.toString()));

  if (msgStatus === 'submitted') {
    rightDiv.appendChild(buildSubmittedElement());
  }
  rightDiv.appendChild(collectDiv);
  messageDiv.append(textDiv, rightDiv);

  const deleteButton = createDeleteButton(messageDiv);
  messageDiv.appendChild(deleteButton);

  // 左滑手势
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
    if (Date.now() - draggingStartTime < dragThreshold) return;
    currentX = e.touches[0].clientX;
    const diffX = startX - currentX;

    if (diffX > 0) {
      const translateX = Math.min(diffX, 80);
      messageDiv.style.transform = `translateX(-${translateX}px)`;
      deleteButton.style.transform = `translateX(calc(100% - ${translateX}px))`;
    }
  };

  const handleTouchEnd = () => {
    if (!isDragging) return;
    if (Date.now() - draggingStartTime < dragThreshold) return;

    isDragging = false;

    const diffX = startX - currentX;

    if (diffX > 40) {
      clearSlidingElements();
      messageDiv.style.transform = 'translateX(-80px)';
      deleteButton.style.transform = 'translateX(calc(100% - 80px))';
      slidingElements.add(messageDiv);
    } else {
      messageDiv.style.transform = 'translateX(0)';
      deleteButton.style.transform = 'translateX(100%)';
      slidingElements.delete(messageDiv);
    }
  };

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
export async function appendMessage(listElement: HTMLElement, msg: Message, animate: boolean = true): Promise<HTMLElement> {
  const { id } = msg;
  messageStorage.set(id, msg);

  const messageDiv = buildMessageElement(msg);
  listElement.firstElementChild.appendChild(messageDiv);

  if (animate) {
    messageDiv.classList.add('message-enter');
    messageDiv.addEventListener('animationend', () => {
      messageDiv.classList.remove('message-enter');
    }, { once: true });

    // 金额计数动画（currency 在独立 span 中，无需拼接）
    messageDiv.querySelectorAll<HTMLElement>('[data-amount-target]').forEach(el => {
      const target = parseFloat(el.dataset.amountTarget!);
      if (!isNaN(target) && target > 0) {
        animateAmount(el, target);
      }
    });
  }

  return messageDiv;
}

// 显示错误提示
export async function showErrorDialog(errorDialog: HTMLElement, message: string): Promise<void> {
  const textSpan = errorDialog.querySelector('span');
  if (textSpan) {
    textSpan.textContent = message;
  }
  errorDialog.classList.remove('hidden');
  await new Promise(resolve => setTimeout(resolve, 3000));
  errorDialog.classList.add('hidden');
}

// Tab 按钮样式：active/inactive 各主题的 class 集合
const TAB_ACTIVE_CLASSES = ['bg-blue-500', 'dark:bg-accent', 'text-white', 'dark:glow-accent'];
const TAB_INACTIVE_CLASSES = ['bg-gray-100', 'dark:bg-white/5', 'text-gray-600', 'dark:text-gray-400'];

// 切换标签页（滑动）
export function switchTab(tab: string): void {
  if (tabSlider) {
    tabSlider.style.transform = tab === 'history' ? 'translateX(0)' : 'translateX(-100%)';
  }

  document.querySelectorAll<HTMLButtonElement>('[data-tab-button]').forEach(btn => {
    const isActive = btn.dataset.tabButton === tab;
    // 移除所有状态 class，再添加对应状态
    [...TAB_ACTIVE_CLASSES, ...TAB_INACTIVE_CLASSES].forEach(c => btn.classList.remove(c));
    const classes = isActive ? TAB_ACTIVE_CLASSES : TAB_INACTIVE_CLASSES;
    btn.classList.add(...classes);
  });
}

// 标记按钮操作成功
export async function markButtonSuccess(button: HTMLButtonElement): Promise<void> {
  const originalButtonText = button.textContent ?? '';

  button.disabled = true;
  button.classList.remove('bg-blue-500', 'hover:bg-blue-600', 'dark:bg-accent', 'dark:hover:bg-violet-500');
  button.classList.add('bg-green-500', 'dark:bg-emerald-500');
  button.textContent = 'Done!';
  await new Promise(resolve => setTimeout(resolve, 1000));

  button.disabled = false;
  button.classList.remove('bg-green-500', 'dark:bg-emerald-500');
  button.classList.add('bg-blue-500', 'hover:bg-blue-600', 'dark:bg-accent', 'dark:hover:bg-violet-500');
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

  // 移除关闭动画残留
  transactionDialog.classList.remove('sheet-closing');

  dialogOverlay.classList.remove('hidden');
  transactionDialog.classList.remove('hidden');

  resetAmountDisplay();

  [messageHistory, messageFavorites].forEach((list: HTMLElement) => {
    list.scrollTop = list.scrollHeight;
  });
}

// 隐藏交易对话框（带关闭动画）
export function hideTransactionDialog(): void {
  // Sheet 关闭动画
  transactionDialog.classList.add('sheet-closing');

  const handleAnimationEnd = () => {
    if (!transactionDialog.classList.contains('sheet-closing')) return;
    transactionDialog.classList.remove('sheet-closing');
    transactionDialog.classList.add('hidden');
    numpadContainer.classList.add('hidden');
    modifyAmountButton.classList.remove('hidden');
    submitWithAmountButton.classList.add('hidden');
  };

  transactionDialog.addEventListener('animationend', handleAnimationEnd, { once: true });

  // 遮罩淡出
  dialogOverlay.classList.add('hidden');
}

// 提取交易金额
export function extractAmount(text: string): string | null {
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
  if (amountDisplay.textContent === amountDisplay.dataset.originalAmount) {
    amountDisplay.textContent = '';
  }

  if (value === '.' && amountDisplay.textContent.includes('.')) {
    return;
  }

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
    });
  } catch (error) {
    console.error('Error toggling favorite:', error);
    await showErrorDialog(errorDialog, error.message || 'Toggle favorite failed. Please check console for details.');
  }
}

// 骨架卡片
export function buildSkeletonCard(): HTMLElement {
  const card = createElement<HTMLDivElement>('div', {
    classes: ['skeleton-card', 'flex', 'items-center', 'p-2', 'w-full', 'h-16']
  });

  const textPlaceholder = createElement<HTMLDivElement>('div', {
    classes: ['flex-1', 'h-4', 'bg-gray-200', 'dark:bg-white/5', 'rounded']
  });

  const iconPlaceholder = createElement<HTMLDivElement>('div', {
    classes: ['w-8', 'h-8', 'bg-gray-200', 'dark:bg-white/5', 'rounded-full', 'ml-2']
  });

  card.append(textPlaceholder, iconPlaceholder);
  return card;
}
