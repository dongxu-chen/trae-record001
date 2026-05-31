import { useState, useCallback, useEffect } from 'react';
import { useGraphStore } from '../store/useGraphStore';
import { validateExpression } from '../utils/expressionParser';
import { PRESET_COLORS } from '../utils/colors';

export const useFunction = () => {
  const { addFunction, removeFunction, toggleFunctionVisibility, toggleDerivative, updateFunctionColor } =
    useGraphStore();
  const [inputExpression, setInputExpression] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);
  const [isValidating, setIsValidating] = useState(false);
  const [selectedColor, setSelectedColor] = useState(PRESET_COLORS[0]);

  useEffect(() => {
    if (!inputExpression.trim()) {
      setValidationError(null);
      return;
    }

    const timer = setTimeout(() => {
      setIsValidating(true);
      const result = validateExpression(inputExpression);
      if (!result.valid) {
        setValidationError(result.error || '表达式无效');
      } else {
        setValidationError(null);
      }
      setIsValidating(false);
    }, 300);

    return () => clearTimeout(timer);
  }, [inputExpression]);

  const handleAddFunction = useCallback(() => {
    if (!inputExpression.trim()) return;

    const result = addFunction(inputExpression.trim(), selectedColor);
    if (result.success) {
      setInputExpression('');
      setValidationError(null);
    } else {
      setValidationError(result.error || '添加函数失败');
    }
  }, [inputExpression, addFunction, selectedColor]);

  const handleKeyPress = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter' && !validationError && inputExpression.trim()) {
        handleAddFunction();
      }
    },
    [handleAddFunction, validationError, inputExpression]
  );

  return {
    inputExpression,
    setInputExpression,
    validationError,
    isValidating,
    selectedColor,
    setSelectedColor,
    handleAddFunction,
    handleKeyPress,
    removeFunction,
    toggleFunctionVisibility,
    toggleDerivative,
    updateFunctionColor,
  };
};
