import './style.css';
import './icons.js';
import { initLocale } from './i18n.js';
import { fetchMessages, sendChatMessage, submitTransaction, cloneTransaction, submitTransactionWithAmount as cloneTransactionWithAmount } from './api.js';
import {
  buildSubmittedElement, appendMessage, showErrorDialog, switchTab, markButtonSuccess,
  showTransactionDialog, hideTransactionDialog, showNumpad,
  handleNumpadInput, clearAmountDisplay, buildSkeletonCard
} from './ui.js';
import {
  messageHistory, errorDialog, messageInput, sendButton, submitTransactionButton, transactionText,
  cloneTransactionButton, closeDialogButton, messageFavorites,
  dialogOverlay, modifyAmountButton, submitWithAmountButton, amountDisplay, numpadClearButton, numpadButtons
} from './storage.js';
import { triggerConfetti } from './confetti.js';
import { registerSW } from 'virtual:pwa-register';


// 初始化消息列表
async function initMessages(): Promise<void> {
  // 显示骨架卡片
  const skeletonCount = 5;
  const skeletonFragment = document.createDocumentFragment();
  for (let i = 0; i < skeletonCount; i++) {
    skeletonFragment.appendChild(buildSkeletonCard());
  }
  messageHistory.firstElementChild.appendChild(skeletonFragment);

  try {
    const { messages, favorites } = await fetchMessages();
    // 移除骨架
    messageHistory.firstElementChild.innerHTML = '';

    messages.forEach(async msg => {
      await appendMessage(messageHistory, msg, false);
    });
    favorites.forEach(async msg => {
      await appendMessage(messageFavorites, msg, false);
    });
    messageHistory.scrollTop = messageHistory.scrollHeight;
  } catch (error) {
    console.error('Error fetching messages:', error);
    messageHistory.firstElementChild.innerHTML = '';
    await showErrorDialog(errorDialog, 'Failed to fetch messages. Please check console for details.');
  }
}

// 发送消息
async function handleSendMessage() {
  const message = messageInput.value;
  if (message === '') {
    return;
  }

  sendButton.disabled = true;
  try {
    const data = await sendChatMessage(message);
    messageInput.value = '';
    await appendMessage(messageHistory, data);
    switchTab('history');
    messageHistory.scrollTop = messageHistory.scrollHeight;
    showTransactionDialog(data.id);
  } catch (error) {
    console.error('Error sending message:', error);
    await showErrorDialog(errorDialog, error.message || 'Failed to send message. Please check console for details.');
  } finally {
    sendButton.disabled = false;
  }
}

// 处理交易操作
async function handleTransactionAction(action: 'submit' | 'clone' | 'clone_with_amount', msgId: string, button: HTMLButtonElement, amount?: string): Promise<void> {
  button.disabled = true;
  try {
    if (action === 'submit') {
      await submitTransaction(Number(msgId));
    } else if (action === 'clone') {
      await cloneTransaction(Number(msgId));
    } else if (action === 'clone_with_amount' && amount) {
      await cloneTransactionWithAmount(Number(msgId), amount);
    }

    // 更新消息状态
    const messageElements = document.querySelectorAll<HTMLDivElement>(`[data-msg-id="${msgId}"]>div.right-container`);
    messageElements.forEach((ele: HTMLDivElement) => {
      if (ele.querySelector('.ele-check') === null) {
        ele.insertBefore(buildSubmittedElement(), ele.firstChild);
      }
    });

    await markButtonSuccess(button);

    // 提交成功 → confetti
    const rect = button.getBoundingClientRect();
    triggerConfetti(rect.left + rect.width / 2, rect.top + rect.height / 2);

    hideTransactionDialog();
  } catch (error) {
    console.error(`Error during transaction ${action}:`, error);
    await showErrorDialog(errorDialog, error.message || `Transaction ${action} failed. Please check console for details.`);
  } finally {
    button.disabled = false;
  }
}

// 注册事件监听器
function registerEventListeners(): void {
  sendButton.addEventListener('click', handleSendMessage);
  messageInput.addEventListener('keydown', async (event) => {
    if (event.key === 'Enter') {
      await handleSendMessage();
    }
  });

  submitTransactionButton.addEventListener('click', async () => {
    const msgId = transactionText.dataset.msgId as string;
    await handleTransactionAction('submit', msgId, submitTransactionButton);
  });

  cloneTransactionButton.addEventListener('click', async () => {
    const msgId = transactionText.dataset.msgId as string;
    await handleTransactionAction('clone', msgId, cloneTransactionButton);
  });

  modifyAmountButton.addEventListener('click', () => {
    showNumpad();
  });

  submitWithAmountButton.addEventListener('click', async () => {
    const msgId = transactionText.dataset.msgId as string;
    const amount = amountDisplay.textContent;
    if (amount) {
      await handleTransactionAction('clone_with_amount', msgId, submitWithAmountButton, amount);
    }
  });

  numpadButtons.forEach(button => {
    button.addEventListener('click', () => {
      handleNumpadInput(button.textContent);
    });
  });

  numpadClearButton.addEventListener('click', clearAmountDisplay);

  closeDialogButton.addEventListener('click', () => {
    hideTransactionDialog();
  });

  dialogOverlay.addEventListener('click', () => {
    hideTransactionDialog();
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      hideTransactionDialog();
    }
  });

  document.querySelectorAll<HTMLButtonElement>('[data-tab-button]').forEach(btn => {
    btn.addEventListener('click', () => {
      switchTab(btn.dataset.tabButton);
    });
  });
}

// 初始化应用
document.addEventListener('DOMContentLoaded', async () => {
  registerEventListeners();
  await Promise.all([initLocale(), initMessages()]);
});

// Service worker 配置
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
    if (window.confirm(`There is a new version of this app available. Do you want to update?`)) {
      updateSW();
    }
  },
  onOfflineReady: () => {
    showErrorDialog(errorDialog, 'This app is offline.');
  }
});
