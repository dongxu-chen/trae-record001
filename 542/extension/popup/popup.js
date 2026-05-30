(function () {
  const mainToggle = document.getElementById('mainToggle');
  const categorySection = document.getElementById('categorySection');
  const typeButtons = document.querySelectorAll('.type-btn');

  let isEnabled = false;
  let selectedType = 'protanopia';

  function updateUI() {
    if (isEnabled) {
      mainToggle.classList.add('active');
      categorySection.style.display = 'block';
    } else {
      mainToggle.classList.remove('active');
      categorySection.style.display = 'none';
    }

    typeButtons.forEach((btn) => {
      if (btn.dataset.type === selectedType && isEnabled) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });
  }

  function sendMessage(action, type) {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]?.id) {
        chrome.tabs.sendMessage(tabs[0].id, { action, type });
      }
    });
  }

  mainToggle.addEventListener('click', () => {
    isEnabled = !isEnabled;
    updateUI();
    sendMessage(isEnabled ? 'enable' : 'disable', selectedType);
  });

  typeButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      selectedType = btn.dataset.type;
      isEnabled = true;
      updateUI();
      sendMessage('enable', selectedType);
    });
  });

  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs[0]?.id) {
      chrome.tabs.sendMessage(tabs[0].id, { action: 'getStatus' }, (response) => {
        if (response) {
          isEnabled = response.isEnabled;
          selectedType = response.type;
          updateUI();
        }
      });
    }
  });

  updateUI();
})();
