import './style.css';
import './icons.js';
import { initLocale } from './i18n.js';
import { fetchMessages, sendChatMessage, submitTransaction, cloneTransaction, submitTransactionWithAmount as cloneTransactionWithAmount } from './api.js';
import { 
  buildSubmittedElement, appendMessage, showErrorDialog, switchTab, markButtonSuccess, 
  showTransactionDialog, hideTransactionDialog, showNumpad, hideNumpad, 
  handleNumpadInput, clearAmountDisplay, resetAmountDisplay
} from './ui.js';
import {
  messageHistory, errorDialog, messageInput, sendButton, submitTransactionButton, transactionText, 
  cloneTransactionButton, closeDialogButton, messageFavorites, loadingIndicator, transactionDialog,
  modifyAmountButton, submitWithAmountButton, numpadContainer, amountDisplay, numpadClearButton, numpadButtons
} from './storage.js';
import { registerSW } from 'virtual:pwa-register';


// 初始化消息列表
async function initMessages(): Promise<void> {
  try {
    const { messages, favorites } = await fetchMessages();
    messages.forEach(async msg => {
      await appendMessage(messageHistory, msg);
    });
    favorites.forEach(async msg => {
      await appendMessage(messageFavorites, msg);
    });
    messageHistory.scrollTop = messageHistory.scrollHeight;
  } catch (error) {
    console.error('Error fetching messages:', error);
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
  // 发送消息
  sendButton.addEventListener('click', handleSendMessage);
  messageInput.addEventListener('keydown', async (event) => {
    if (event.key === 'Enter') {
      await handleSendMessage();
    }
  });

  // 交易操作
  submitTransactionButton.addEventListener('click', async () => {
    const msgId = transactionText.dataset.msgId as string;
    await handleTransactionAction('submit', msgId, submitTransactionButton);
  });
  
  cloneTransactionButton.addEventListener('click', async () => {
    const msgId = transactionText.dataset.msgId as string;
    await handleTransactionAction('clone', msgId, cloneTransactionButton);
  });
  
  // 修改金额按钮
  modifyAmountButton.addEventListener('click', () => {
    showNumpad();
  });
  
  // 提交修改金额
  submitWithAmountButton.addEventListener('click', async () => {
    const msgId = transactionText.dataset.msgId as string;
    const amount = amountDisplay.textContent;
    if (amount) {
      await handleTransactionAction('clone_with_amount', msgId, submitWithAmountButton, amount);
    }
  });
  
  // 数字键盘按钮
  numpadButtons.forEach(button => {
    button.addEventListener('click', () => {
      handleNumpadInput(button.textContent);
    });
  });
  
  // 清除按钮
  numpadClearButton.addEventListener('click', clearAmountDisplay);

  // 对话框操作
  closeDialogButton.addEventListener('click', () => {
    hideTransactionDialog();
  });
  
  document.addEventListener('click', (event: MouseEvent) => {
    if (!transactionDialog.contains(event.target as Node | null) && !((event.target as HTMLElement)?.classList.contains('message'))) {
      hideTransactionDialog();
    }
  });
  
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      hideTransactionDialog();
    }
  });

  // 标签页切换
  document.querySelectorAll<HTMLButtonElement>('[data-tab-button]').forEach(btn => {
    btn.addEventListener('click', () => {
      switchTab(btn.dataset.tabButton);
    });
  });
}

// 初始化应用
document.addEventListener('DOMContentLoaded', async () => {
  registerEventListeners();
  
  loadingIndicator.classList.replace('hidden', 'flex');
  await Promise.all([initLocale(), initMessages()]);
  loadingIndicator.classList.replace('flex', 'hidden');
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