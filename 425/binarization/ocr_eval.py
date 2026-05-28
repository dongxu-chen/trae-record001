import os
import numpy as np
import cv2
from typing import Dict, Optional, Tuple, List, Any
from dataclasses import dataclass
from .core import binarize_pipeline

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False


@dataclass
class OCRWord:
    text: str
    confidence: float
    left: int
    top: int
    width: int
    height: int
    line_num: int
    word_num: int


@dataclass
class OCRResult:
    full_text: str
    avg_confidence: float
    words: List[OCRWord]
    num_words: int
    num_lines: int
    char_count: int
    high_confidence_ratio: float


def ocr_text(image: np.ndarray, lang: str = "eng", psm: int = 6) -> str:
    if not TESSERACT_AVAILABLE:
        return "[Tesseract not installed]"
    try:
        config = f"--psm {psm}"
        text = pytesseract.image_to_string(image, lang=lang, config=config)
        return text.strip()
    except Exception as e:
        return f"[OCR Error: {str(e)}]"


def ocr_full_analysis(image: np.ndarray, lang: str = "eng", psm: int = 6) -> OCRResult:
    empty_result = OCRResult(
        full_text="",
        avg_confidence=0.0,
        words=[],
        num_words=0,
        num_lines=0,
        char_count=0,
        high_confidence_ratio=0.0,
    )

    if not TESSERACT_AVAILABLE:
        empty_result.full_text = "[Tesseract not installed]"
        return empty_result

    try:
        config = f"--psm {psm}"
        data = pytesseract.image_to_data(image, lang=lang, config=config, output_type=pytesseract.Output.DICT)

        words: List[OCRWord] = []
        confidences: List[float] = []
        text_parts: List[str] = []
        line_numbers: set = set()

        n = len(data.get("text", []))
        for i in range(n):
            try:
                conf = float(data["conf"][i])
                text = data["text"][i]
                if conf >= 0 and text.strip():
                    word = OCRWord(
                        text=text,
                        confidence=conf,
                        left=int(data["left"][i]),
                        top=int(data["top"][i]),
                        width=int(data["width"][i]),
                        height=int(data["height"][i]),
                        line_num=int(data["line_num"][i]),
                        word_num=int(data["word_num"][i]),
                    )
                    words.append(word)
                    confidences.append(conf)
                    text_parts.append(text)
                    line_numbers.add(word.line_num)
            except (ValueError, IndexError, KeyError):
                continue

        full_text = " ".join(text_parts).strip()
        avg_conf = float(np.mean(confidences)) if confidences else 0.0
        high_conf_count = sum(1 for c in confidences if c >= 70)
        high_conf_ratio = high_conf_count / len(confidences) if confidences else 0.0

        return OCRResult(
            full_text=full_text,
            avg_confidence=avg_conf,
            words=words,
            num_words=len(words),
            num_lines=len(line_numbers),
            char_count=len(full_text),
            high_confidence_ratio=high_conf_ratio,
        )
    except Exception as e:
        empty_result.full_text = f"[OCR Error: {str(e)}]"
        return empty_result


def ocr_confidence(image: np.ndarray, lang: str = "eng", psm: int = 6) -> Tuple[str, float]:
    result = ocr_full_analysis(image, lang=lang, psm=psm)
    return result.full_text, result.avg_confidence


def evaluate_binarization(
    image_path: str,
    method: str = "sauvola",
    denoise: bool = True,
    denoise_method: str = "wavelet",
    bg_estimation: str = "none",
    bg_kernel_size: int = 51,
    bg_degree: int = 2,
    bg_texture_suppress: bool = True,
    bg_texture_kernel: int = 7,
    bg_texture_method: str = "median",
    bg_smooth_sigma: float = 3.0,
    bg_downsample: int = 4,
    window_size: int = 15,
    k: float = 0.2,
    r: float = 128.0,
    block_size: int = 11,
    C: int = 2,
    post_process: bool = True,
    morph_kernel: int = 1,
    lang: str = "eng",
    psm: int = 6,
    reference_text: Optional[str] = None,
) -> Dict:
    img = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        img = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
    if img is None:
        return {"error": "无法读取图像"}

    orig_result = ocr_full_analysis(img, lang=lang, psm=psm)

    binary = binarize_pipeline(
        img,
        method=method,
        denoise=denoise,
        denoise_method=denoise_method,
        bg_estimation=bg_estimation,
        bg_kernel_size=bg_kernel_size,
        bg_degree=bg_degree,
        bg_texture_suppress=bg_texture_suppress,
        bg_texture_kernel=bg_texture_kernel,
        bg_texture_method=bg_texture_method,
        bg_smooth_sigma=bg_smooth_sigma,
        bg_downsample=bg_downsample,
        window_size=window_size,
        k=k,
        r=r,
        block_size=block_size,
        C=C,
        post_process=post_process,
        morph_kernel=morph_kernel,
    )

    bin_result = ocr_full_analysis(binary, lang=lang, psm=psm)

    result = {
        "image_path": image_path,
        "method": method,
        "original": {
            "text": orig_result.full_text,
            "avg_confidence": round(orig_result.avg_confidence, 2),
            "num_words": orig_result.num_words,
            "num_lines": orig_result.num_lines,
            "char_count": orig_result.char_count,
            "high_conf_ratio": round(orig_result.high_confidence_ratio, 4),
            "words": [
                {
                    "text": w.text,
                    "confidence": round(w.confidence, 2),
                    "bbox": [w.left, w.top, w.width, w.height],
                }
                for w in orig_result.words
            ],
        },
        "binary": {
            "text": bin_result.full_text,
            "avg_confidence": round(bin_result.avg_confidence, 2),
            "num_words": bin_result.num_words,
            "num_lines": bin_result.num_lines,
            "char_count": bin_result.char_count,
            "high_conf_ratio": round(bin_result.high_confidence_ratio, 4),
            "words": [
                {
                    "text": w.text,
                    "confidence": round(w.confidence, 2),
                    "bbox": [w.left, w.top, w.width, w.height],
                }
                for w in bin_result.words
            ],
        },
        "confidence_improvement": round(bin_result.avg_confidence - orig_result.avg_confidence, 2),
        "word_count_improvement": bin_result.num_words - orig_result.num_words,
        "high_conf_ratio_improvement": round(
            bin_result.high_confidence_ratio - orig_result.high_confidence_ratio, 4
        ),
    }

    if reference_text:
        ref = reference_text.lower().strip()
        orig_char_acc, orig_alignment = char_level_accuracy(
            orig_result.full_text.lower().strip(), ref
        )
        bin_char_acc, bin_alignment = char_level_accuracy(
            bin_result.full_text.lower().strip(), ref
        )
        result["reference_text"] = reference_text
        result["original_char_accuracy"] = round(orig_char_acc, 4)
        result["binary_char_accuracy"] = round(bin_char_acc, 4)
        result["char_accuracy_improvement"] = round(bin_char_acc - orig_char_acc, 4)
        result["original_char_alignment"] = orig_alignment
        result["binary_char_alignment"] = bin_alignment
        result["char_error_rate_original"] = round(1 - orig_char_acc, 4)
        result["char_error_rate_binary"] = round(1 - bin_char_acc, 4)

    return result


def char_level_accuracy(pred: str, ref: str) -> Tuple[float, Dict[str, Any]]:
    if not ref:
        return 0.0, {"alignment": [], "correct": 0, "insertions": 0, "deletions": 0, "substitutions": 0}
    if not pred:
        return 0.0, {"alignment": [], "correct": 0, "insertions": 0, "deletions": 0, "substitutions": 0}

    m = len(ref)
    n = len(pred)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    backtrack = [[None] * (n + 1) for _ in range(m + 1)]

    for i in range(m + 1):
        dp[i][0] = i
        backtrack[i][0] = "delete"
    for j in range(n + 1):
        dp[0][j] = j
        backtrack[0][j] = "insert"

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if ref[i - 1] == pred[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
                backtrack[i][j] = "match"
            else:
                delete_cost = dp[i - 1][j] + 1
                insert_cost = dp[i][j - 1] + 1
                substitute_cost = dp[i - 1][j - 1] + 1

                min_cost = min(delete_cost, insert_cost, substitute_cost)
                if min_cost == substitute_cost:
                    dp[i][j] = substitute_cost
                    backtrack[i][j] = "substitute"
                elif min_cost == delete_cost:
                    dp[i][j] = delete_cost
                    backtrack[i][j] = "delete"
                else:
                    dp[i][j] = insert_cost
                    backtrack[i][j] = "insert"

    i, j = m, n
    alignment = []
    correct = insertions = deletions = substitutions = 0

    while i > 0 or j > 0:
        op = backtrack[i][j]
        if op == "match":
            alignment.append({"ref_char": ref[i - 1], "pred_char": pred[j - 1], "type": "correct"})
            correct += 1
            i -= 1
            j -= 1
        elif op == "substitute":
            alignment.append({"ref_char": ref[i - 1], "pred_char": pred[j - 1], "type": "substitute"})
            substitutions += 1
            i -= 1
            j -= 1
        elif op == "delete":
            alignment.append({"ref_char": ref[i - 1], "pred_char": "", "type": "delete"})
            deletions += 1
            i -= 1
        elif op == "insert":
            alignment.append({"ref_char": "", "pred_char": pred[j - 1], "type": "insert"})
            insertions += 1
            j -= 1

    alignment.reverse()
    distance = dp[m][n]
    accuracy = max(0.0, 1.0 - distance / max(m, n))

    details = {
        "alignment": alignment,
        "correct": correct,
        "insertions": insertions,
        "deletions": deletions,
        "substitutions": substitutions,
        "edit_distance": distance,
        "ref_length": m,
        "pred_length": n,
    }

    return accuracy, details


def _char_accuracy(pred: str, ref: str) -> float:
    accuracy, _ = char_level_accuracy(pred, ref)
    return accuracy