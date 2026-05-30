const COLORBLIND_MATRICES = {
  protanopia: '0.567 0.433 0 0 0 0.558 0.442 0 0 0 0 0.242 0.758 0 0 0 0 0 1 0',
  protanomaly: '0.817 0.183 0 0 0 0.333 0.667 0 0 0 0 0.125 0.875 0 0 0 0 0 1 0',
  deuteranopia: '0.625 0.375 0 0 0 0.7 0.3 0 0 0 0 0.3 0.7 0 0 0 0 0 1 0',
  deuteranomaly: '0.8 0.2 0 0 0 0.258 0.742 0 0 0 0 0.142 0.858 0 0 0 0 0 1 0',
  tritanopia: '0.95 0.05 0 0 0 0 0.433 0.567 0 0 0 0.475 0.525 0 0 0 0 0 1 0',
  tritanomaly: '0.967 0.033 0 0 0 0 0.733 0.267 0 0 0 0.183 0.817 0 0 0 0 0 1 0',
  achromatopsia: '0.299 0.587 0.114 0 0 0.299 0.587 0.114 0 0 0.299 0.587 0.114 0 0 0 0 0 1 0',
  achromatomaly: '0.618 0.32 0.062 0 0 0.163 0.775 0.062 0 0 0.163 0.32 0.516 0 0 0 0 0 1 0',
};

let currentState = {
  isEnabled: false,
  type: 'protanopia',
};

function createSvgFilters() {
  const existing = document.getElementById('colora11y-svg-filters');
  if (existing) existing.remove();

  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('id', 'colora11y-svg-filters');
  svg.setAttribute('style', 'position:absolute;width:0;height:0;');

  for (const [type, values] of Object.entries(COLORBLIND_MATRICES)) {
    const filter = document.createElementNS('http://www.w3.org/2000/svg', 'filter');
    filter.setAttribute('id', `colora11y-${type}`);

    const matrix = document.createElementNS('http://www.w3.org/2000/svg', 'feColorMatrix');
    matrix.setAttribute('type', 'matrix');
    matrix.setAttribute('values', values);

    filter.appendChild(matrix);
    svg.appendChild(filter);
  }

  document.documentElement.appendChild(svg);
}

function applyFilter(type) {
  document.documentElement.style.filter = `url(#colora11y-${type})`;
}

function removeFilter() {
  document.documentElement.style.filter = 'none';
}

function handleEnable(type) {
  currentState.isEnabled = true;
  currentState.type = type;
  createSvgFilters();
  applyFilter(type);
}

function handleDisable() {
  currentState.isEnabled = false;
  removeFilter();
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.action === 'enable') {
    handleEnable(message.type);
  } else if (message.action === 'disable') {
    handleDisable();
  } else if (message.action === 'getStatus') {
    sendResponse(currentState);
  }
  return true;
});
