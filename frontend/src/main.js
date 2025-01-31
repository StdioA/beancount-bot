import './style.css'

const messageHistory = document.getElementById('message-history');
const messageInput = document.getElementById('message-input');
const sendButton = document.getElementById('send-button');
const transactionDialog = document.getElementById('transaction-dialog');
const transactionText = document.getElementById('transaction-text');
const submitTransactionButton = document.getElementById('submit-transaction');
const cloneTransactionButton = document.getElementById('clone-transaction');
const closeDialogButton = document.getElementById('close-dialog');
const errorDialog = document.getElementById('error-dialog');

async function fetchMessages() {
  const response = await fetch('/api/messages');
  const data = await response.json();
  data.messages.forEach(msg => {
    appendMessage(msg);
  })
}

document.addEventListener('DOMContentLoaded', async () => {
  await fetchMessages();
});

sendButton.addEventListener('click', async () => {
  const message = messageInput.value;
  if (message) {
    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message })
      });
      const data = await response.json();
      if (response.ok) {
        appendMessage(data);
        messageInput.value = '';
      } else {
        throw new Error(data.error);
      }
    } catch (error) {
      await popupError(error.message);
    }
  }
});

closeDialogButton.addEventListener('click', () => {
  transactionDialog.classList.add('hidden');
});

document.addEventListener('click', (event) => {
  if (!transactionDialog.contains(event.target) && !event.target.classList.contains('message')) {
    transactionDialog.classList.add('hidden');
  }
});

submitTransactionButton.addEventListener('click', async () => {
  const msgId = transactionText.dataset.msgId;
  submitTransactionButton.disabled = true;
  try {
    await fetch(`/api/submit`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ id: Number(msgId) })
    });
    // Find the message element and update its status
    const messageElement = document.querySelector(`[data-msg-id="${msgId}"]`);
    if (messageElement) {
      messageElement.classList.remove('bg-gray-200');
      messageElement.classList.add('bg-green-200');
    }
    await markButtonSuccess(submitTransactionButton);
  } finally {
    submitTransactionButton.disabled = false;
  }
});

cloneTransactionButton.addEventListener('click', async () => {
  const msgId = transactionText.dataset.msgId;
  cloneTransactionButton.disabled = true;
  try {
    await fetch(`/api/clone`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ id: Number(msgId) })
    });
    await markButtonSuccess(cloneTransactionButton);
  } finally {
    cloneTransactionButton.disabled = false;
  }
});


function appendMessage(msg) {
  const {id, message, transaction_text, status} = msg;
  const messageDiv = document.createElement('div');
  messageDiv.classList.add('message', 'mb-2', 'p-2', 'rounded-md', 'cursor-pointer', 'self-start', 'text-left');
  if (msg.status == 'submitted') {
    messageDiv.classList.add('bg-green-200');
  } else {
    messageDiv.classList.add('bg-gray-200');
  }
  messageDiv.textContent = message;
  messageDiv.dataset.msgId = id;
  if (transaction_text) {
    messageDiv.dataset.transactionText = transaction_text;
  }
  if (transaction_text) {
    messageDiv.addEventListener('click', (event) => {
      transactionText.textContent = transaction_text;
      transactionText.dataset.msgId = id;
      if (status == 'submitted') {
        submitTransactionButton.classList.add('hidden');
        cloneTransactionButton.classList.remove('hidden');
      } else {
        cloneTransactionButton.classList.add('hidden');
        submitTransactionButton.classList.remove('hidden');
      }
      transactionDialog.classList.remove('hidden');
      event.stopPropagation(); // Prevent document click from immediately closing dialog
    });
  }
  messageHistory.appendChild(messageDiv);
  messageHistory.scrollTop = messageHistory.scrollHeight;
}

async function markButtonSuccess(button) {
  const originalButtonText = button.textContent;

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

async function popupError(message) {
  errorDialog.textContent = message;
  errorDialog.classList.remove('hidden');
  await new Promise(resolve => setTimeout(resolve, 3000));
  errorDialog.classList.add('hidden');
}
