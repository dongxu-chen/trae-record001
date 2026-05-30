chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.action === 'enable' || message.action === 'disable') {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]?.id) {
        chrome.tabs.sendMessage(tabs[0].id, message);
      }
    });
  }
  return true;
});
