const LOADED_THEMES = new Set<string>();
const STYLE_ELEMENTS: Record<string, HTMLStyleElement> = {};

export async function loadTheme(theme: 'dark' | 'light'): Promise<void> {
  if (LOADED_THEMES.has(theme)) {
    return;
  }

  try {
    let cssContent: string;
    
    if (theme === 'dark') {
      const module = await import('../styles/theme-dark.css?inline');
      cssContent = module.default;
    } else {
      const module = await import('../styles/theme-light.css?inline');
      cssContent = module.default;
    }

    const styleElement = document.createElement('style');
    styleElement.id = `code-snippet-theme-${theme}`;
    styleElement.textContent = cssContent;
    
    document.head.appendChild(styleElement);
    
    STYLE_ELEMENTS[theme] = styleElement;
    LOADED_THEMES.add(theme);
  } catch (error) {
    console.error(`Failed to load theme ${theme}:`, error);
  }
}

export function removeTheme(theme: 'dark' | 'light'): void {
  const styleElement = STYLE_ELEMENTS[theme];
  if (styleElement) {
    document.head.removeChild(styleElement);
    delete STYLE_ELEMENTS[theme];
    LOADED_THEMES.delete(theme);
  }
}

export function unloadAllThemes(): void {
  Object.keys(STYLE_ELEMENTS).forEach((theme) => {
    removeTheme(theme as 'dark' | 'light');
  });
}

export function isThemeLoaded(theme: 'dark' | 'light'): boolean {
  return LOADED_THEMES.has(theme);
}
