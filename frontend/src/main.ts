import './style.css';

const messageHistory = document.getElementById('message-history') as HTMLElement;
const messageInput = document.getElementById('message-input') as HTMLInputElement;
const sendButton = document.getElementById('send-button') as HTMLButtonElement;
const transactionDialog = document.getElementById('transaction-dialog') as HTMLElement;
const transactionText = document.getElementById('transaction-text') as HTMLElement;
const submitTransactionButton = document.getElementById('submit-transaction') as HTMLButtonElement;
const cloneTransactionButton = document.getElementById('clone-transaction') as HTMLButtonElement;
const closeDialogButton = document.getElementById('close-dialog') as HTMLButtonElement;
const errorDialog = document.getElementById('error-dialog') as HTMLElement;

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
  const response: Response = await fetch('/api/messages');
  const { messages }: { messages: Message[] } = await response.json();
  messages.forEach(msg => {
    appendMessage(msg);
  });
}

document.addEventListener('DOMContentLoaded', async () => {
  await fetchMessages();
});

sendButton.addEventListener('click', async () => {
  const message = messageInput.value;
  if (message) {
    try {
      const response: Response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message })
      });
      const data: Message | ErrorMessage = await response.json();
      if (response.ok) {
        appendMessage(data as Message);
        messageInput.value = '';
      } else {
        if ('error' in data && data.error) {
          throw new Error(data.error);
        } else {
          throw new Error('Unknown error');
        }
      }
    } catch (error) {
      await popupError(error.message);
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

submitTransactionButton.addEventListener('click', async (event) => {
  const target = event.currentTarget as HTMLButtonElement;
  const msgId = transactionText.dataset.msgId as string;
  target.disabled = true;
  try {
    const response = await fetch(`/api/submit`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ id: Number(msgId) })
    });
    if (response.ok) {
      // Find the message element and update its status
      const messageElement = document.querySelector<HTMLDivElement>(`[data-msg-id="${msgId}"]`);
      if (messageElement) {
        messageElement.classList.remove('bg-gray-200');
        messageElement.classList.add('bg-green-200');
      }
      await markButtonSuccess(target);
    } else {
      const data: ErrorMessage = await response.json();
      throw new Error(data.error);
    }
  } catch (error) {
    await popupError(error.message);
  } finally {
    target.disabled = false;
  }
});

cloneTransactionButton.addEventListener('click', async (event) => {
  const target = event.currentTarget as HTMLButtonElement;
  const msgId = transactionText.dataset.msgId as string;
  target.disabled = true;
  try {
    const response = await fetch(`/api/clone`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ id: Number(msgId) })
    });
    if (response.ok) {
      await markButtonSuccess(target);
    } else {
      const data: ErrorMessage = await response.json();
      throw new Error(data.error);
    }
  } catch (error) {
    await popupError(error.message);
  } finally {
    target.disabled = false;
  }
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
