import { useAppStore } from '@/store/useAppStore';
import { getContrastRatio, meetsWcagAA, meetsWcagAAA } from '@/utils/contrast';
import type { RGB } from '@/types';

export function useContrastChecker() {
  const { contrastIssues, wcagReport, pickedColor, simulatedPickedColor } =
    useAppStore();

  const checkPair = (fg: RGB, bg: RGB) => {
    const ratio = getContrastRatio(fg, bg);
    return {
      ratio,
      aaNormal: meetsWcagAA(ratio, false),
      aaLarge: meetsWcagAA(ratio, true),
      aaaNormal: meetsWcagAAA(ratio, false),
      aaaLarge: meetsWcagAAA(ratio, true),
    };
  };

  return {
    contrastIssues,
    wcagReport,
    pickedColor,
    simulatedPickedColor,
    checkPair,
  };
}
