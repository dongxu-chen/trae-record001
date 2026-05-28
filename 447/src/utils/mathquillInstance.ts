export interface MQMathField {
  latex(): string;
  latex(latex: string): MQMathField;
  cmd(latex: string): MQMathField;
  write(latex: string): MQMathField;
  focus(): MQMathField;
  keystroke(key: string): MQMathField;
  moveToRightEnd(): MQMathField;
  moveToLeftEnd(): MQMathField;
  select(): MQMathField;
  clearSelection(): MQMathField;
  revert(): MQMathField;
  el(): HTMLElement;
}

let mathFieldInstance: MQMathField | null = null;

export function setMathQuillInstance(instance: MQMathField | null): void {
  mathFieldInstance = instance;
}

export function getMathQuillInstance(): MQMathField | null {
  return mathFieldInstance;
}
