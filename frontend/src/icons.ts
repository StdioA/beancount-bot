// 导入FontAwesome核心库
import { library, dom } from '@fortawesome/fontawesome-svg-core';

// 只导入我们需要的图标
import { IconLookup, faTrash, faHistory, faStar, faTimes, faCheck, faCopy, faReceipt, faPaperPlane, faPen } from '@fortawesome/free-solid-svg-icons';

// 将图标添加到库中
library.add(faTrash, faHistory, faStar, faTimes, faCheck, faCopy, faReceipt, faPaperPlane, faPen);

// 自动替换页面上的图标元素
dom.watch();

export function buildIconDom(icon: IconLookup): HTMLElement {
  const iconElement = document.createElement('i');
  iconElement.classList.add(icon.prefix, `fa-${icon.iconName}`);
  return iconElement;
}

// 导出图标以便在其他地方使用
export { faTrash, faHistory, faStar, faTimes, faCheck, faCopy, faReceipt, faPaperPlane, faPen };
