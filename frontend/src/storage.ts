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
export const errorDialog = document.getElementById('error-dialog') as HTMLElement;
export const loadingIndicator = document.getElementById('loading-indicator') as HTMLElement;

export let slidingElements = new Set<HTMLElement>();