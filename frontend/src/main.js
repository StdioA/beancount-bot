import './style.css'

const messageHistory = document.getElementById('message-history');
const messageInput = document.getElementById('message-input');
const sendButton = document.getElementById('send-button');
const transactionDialog = document.getElementById('transaction-dialog');
const transactionText = document.getElementById('transaction-text');
const submitTransactionButton = document.getElementById('submit-transaction');
const closeDialogButton = document.getElementById('close-dialog');
const errorDialog = document.getElementById('error-dialog');

function fetchMessages() {
  fetch('/api/messages')
    .then(response => response.json())
    .then(data => {
      messageHistory.innerHTML = '';
      data.messages.forEach(msg => {
        appendMessage(msg);
      });
    });
}

fetchMessages();

function popupError(message) {
  errorDialog.textContent = message;
  errorDialog.classList.remove('hidden');
  // Close the dialog after 3 seconds
  setTimeout(() => {
    errorDialog.classList.add('hidden');
  }, 3000);
}

sendButton.addEventListener('click', () => {
  const message = messageInput.value;
  if (message) {
    messageInput.value = '';
    fetch('/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ message })
    }).then(response => {
      if (response.ok) {
        return response.json();
      } else {
        return response.text().then(text => {
          throw new Error(text);
        });
      }
    })
      .then(data => {
        appendMessage(data);
      })
      .catch(error => {
        popupError(JSON.parse(error.message).error)
      });
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
  } finally {
    submitTransactionButton.disabled = false;
  }
});


function appendMessage(msg) {
  const {id, message, transaction_text} = msg;
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
      transactionDialog.classList.remove('hidden');
      event.stopPropagation(); // Prevent document click from immediately closing dialog
    });
  }
  messageHistory.appendChild(messageDiv);
  messageHistory.scrollTop = messageHistory.scrollHeight;
}
