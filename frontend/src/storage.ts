import { Message } from './types.js';

// 全局消息存储
export const messageStorage: Map<number, Message> = new Map();

// DOM 元素获取
export const messageHistory = document.getElementById('message-history') as HTMLElement;
export const messageFavorites = document.getElementById('message-favorites') as HTMLElement;
export const messageInput = document.getElementById('message-input') as HTMLInputElement;
export const sendButton = document.getElementById('send-button') as HTMLButtonElement;
export const transactionDialog = document.getElementById('transaction-dialog') as HTMLElement;
export const transactionText = document.getElementById('transaction-text') as HTMLElement;
export const submitTransactionButton = document.getElementById('submit-transaction') as HTMLButtonElement;
export const cloneTransactionButton = document.getElementById('clone-transaction') as HTMLButtonElement;
export const closeDialogButton = document.getElementById('close-dialog') as HTMLButtonElement;
export const dialogOverlay = document.getElementById('dialog-overlay') as HTMLElement;
export const errorDialog = document.getElementById('error-dialog') as HTMLElement;
export const loadingIndicator = document.getElementById('loading-indicator') as HTMLElement;

// 数字键盘相关元素
export const modifyAmountButton = document.getElementById('modify-amount') as HTMLButtonElement;
export const submitWithAmountButton = document.getElementById('submit-with-amount') as HTMLButtonElement;
export const numpadContainer = document.getElementById('numpad-container') as HTMLElement;
export const amountDisplay = document.getElementById('amount-display') as HTMLElement;
export const numpadClearButton = document.getElementById('numpad-clear') as HTMLButtonElement;
export const numpadButtons = document.querySelectorAll('.numpad-btn') as NodeListOf<HTMLButtonElement>;

export const slidingElements = new Set<HTMLElement>();

export const tabSlider = document.getElementById('tab-slider') as HTMLElement;