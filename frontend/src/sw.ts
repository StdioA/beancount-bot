import { registerSW } from 'virtual:pwa-register';
import { showErrorDialog } from './ui.js';
import { errorDialog } from './storage.js';

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