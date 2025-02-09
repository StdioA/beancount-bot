import { registerSW } from 'virtual:pwa-register';
import './style.css';


// 常量定义
const API_MESSAGES = '/api/messages';
const API_CHAT = '/api/chat';
const API_SUBMIT = '/api/submit';
const API_CLONE = '/api/clone';

// DOM 元素获取 (添加类型断言和判空)
const messageHistory = document.getElementById('message-history') as HTMLElement;
const messageInput = document.getElementById('message-input') as HTMLInputElement;
const sendButton = document.getElementById('send-button') as HTMLButtonElement;
const transactionDialog = document.getElementById('transaction-dialog') as HTMLElement;
const transactionText = document.getElementById('transaction-text') as HTMLElement;
const submitTransactionButton = document.getElementById('submit-transaction') as HTMLButtonElement;
const cloneTransactionButton = document.getElementById('clone-transaction') as HTMLButtonElement;
const closeDialogButton = document.getElementById('close-dialog') as HTMLButtonElement;
const errorDialog = document.getElementById('error-dialog') as HTMLElement;
const loadingIndicator = document.getElementById('loading-indicator') as HTMLElement;

interface Message {
  id: number;
  message: string;
  transaction_text: string;
  status: string;
}

interface ErrorMessage {
  error: string;
}

async function fetchMessages(): Promise<void> {
  loadingIndicator.classList.replace('hidden', 'flex');
  try {
    const response: Response = await fetch(API_MESSAGES);
    if (!response.ok) {
      const message = `Failed to fetch messages: ${response.status} ${response.statusText}`;
      console.error(message);
      await popupError(message);
      return;
    }
    const { messages }: { messages: Message[] } = await response.json();
    messages.forEach(msg => {
      appendMessage(msg);
    });
  } catch (error) {
    console.error('Error fetching messages:', error);
    await popupError('Failed to fetch messages. Please check console for details.');
  } finally {
    loadingIndicator.classList.replace('flex', 'hidden');
  }
}

document.addEventListener('DOMContentLoaded', async () => {
  await fetchMessages();
});

sendButton.addEventListener('click', async () => {
  const message = messageInput.value;
  if (message) {
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
      appendMessage(data);
      messageInput.value = '';
    } catch (error) {
      console.error('Error sending message:', error);
      await popupError(error.message || 'Failed to send message. Please check console for details.');
    } finally {
      sendButton.disabled = false;
    }
  }
});

closeDialogButton.addEventListener('click', () => {
  transactionDialog.classList.add('hidden');
});

document.addEventListener('click', (event: MouseEvent) => {
  if (!transactionDialog.contains(event.target as Node | null) && !((event.target as HTMLElement)?.classList.contains('message'))) {
    transactionDialog.classList.add('hidden');
  }
});

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
    const messageElement = document.querySelector<HTMLDivElement>(`[data-msg-id="${msgId}"]`);
    if (messageElement) {
      messageElement.classList.remove('bg-gray-200');
      messageElement.classList.add('bg-green-200');
    }
    await markButtonSuccess(button);
  } catch (error) {
    console.error(`Error during transaction action (${apiEndpoint}):`, error);
    await popupError(error.message || `Transaction action failed. Please check console for details.`);
  } finally {
    button.disabled = false;
  }
}

submitTransactionButton.addEventListener('click', async (event) => {
  const msgId = transactionText.dataset.msgId as string;
  await handleTransactionAction(API_SUBMIT, msgId, submitTransactionButton);
});

cloneTransactionButton.addEventListener('click', async (event) => {
  const msgId = transactionText.dataset.msgId as string;
  await handleTransactionAction(API_CLONE, msgId, cloneTransactionButton);
});

function appendMessage(msg: Message): void {
  const { id, message: msgText, transaction_text: txText, status: msgStatus } = msg;
  const messageDiv = document.createElement('div');
  messageDiv.classList.add(
    'message',
    'mb-2',
    'p-2',
    'rounded-md',
    'cursor-pointer',
    'self-start',
    'text-left',
    msgStatus === 'submitted' ? 'bg-green-200' : 'bg-gray-200',
  );
  messageDiv.textContent = msgText;
  messageDiv.dataset.msgId = id.toString();
  if (txText) {
    messageDiv.dataset.transactionText = txText;

    messageDiv.addEventListener('click', (event) => {
      transactionText.textContent = txText;
      transactionText.dataset.msgId = id.toString();
      const isSubmitted = msgStatus === 'submitted';
      submitTransactionButton.classList.toggle('hidden', isSubmitted);
      cloneTransactionButton.classList.toggle('hidden', !isSubmitted);
      transactionDialog.classList.remove('hidden');
      event.stopPropagation(); // Prevent document click from immediately closing dialog
    });
  }
  messageHistory.appendChild(messageDiv);
  messageHistory.scrollTop = messageHistory.scrollHeight;
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

// 添加 ESC 键监听，关闭对话框 (用户体验改进)
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') {
    transactionDialog.classList.add('hidden');
  }
});


// Service worker 定时检查 & 刷新提示
const intervalMS = 60 * 60 * 1000;

const updateSW = registerSW({
  onRegistered(r) {
    r &&
      setInterval(() => {
        r.update();
      }, intervalMS);
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
