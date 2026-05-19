import Prism from 'prismjs';
import 'prismjs/components/prism-javascript';
import 'prismjs/components/prism-typescript';
import 'prismjs/components/prism-css';
import 'prismjs/components/prism-json';
import 'prismjs/components/prism-markup';
import 'prismjs/components/prism-python';
import 'prismjs/components/prism-java';
import 'prismjs/components/prism-c';
import 'prismjs/components/prism-cpp';
import 'prismjs/components/prism-go';
import 'prismjs/components/prism-rust';
import 'prismjs/components/prism-sql';
import 'prismjs/components/prism-bash';

interface HighlightRequest {
  code: string;
  language: string;
  id: string;
}

interface HighlightResponse {
  html: string;
  id: string;
  success: boolean;
  error?: string;
}

self.onmessage = (e: MessageEvent<HighlightRequest>) => {
  const { code, language, id } = e.data;

  try {
    const grammar = Prism.languages[language];
    if (!grammar) {
      throw new Error(`Unsupported language: ${language}`);
    }

    const html = Prism.highlight(code, grammar, language);

    const response: HighlightResponse = {
      html,
      id,
      success: true,
    };

    self.postMessage(response);
  } catch (error) {
    const response: HighlightResponse = {
      html: '',
      id,
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };

    self.postMessage(response);
  }
};
