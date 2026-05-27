import numpy as np
from typing import Union, Tuple, Optional
from .structuring_element import StructuringElement, create_rect
from .core import erode, dilate, open_op, close_op


def gradient_internal(
    image: np.ndarray,
    structure: Union[np.ndarray, StructuringElement] = None,
    out: Optional[np.ndarray] = None
) -> np.ndarray:
    if structure is None:
        structure = create_rect((3, 3))

    dilated = dilate(image, structure)

    if out is None:
        out = np.empty_like(image)

    np.subtract(dilated.astype(np.int32), image.astype(np.int32), out=out.astype(np.int32))
    np.clip(out, 0, 255, out=out)

    return out.astype(np.uint8)


def gradient_external(
    image: np.ndarray,
    structure: Union[np.ndarray, StructuringElement] = None,
    out: Optional[np.ndarray] = None
) -> np.ndarray:
    if structure is None:
        structure = create_rect((3, 3))

    eroded = erode(image, structure)

    if out is None:
        out = np.empty_like(image)

    np.subtract(image.astype(np.int32), eroded.astype(np.int32), out=out.astype(np.int32))
    np.clip(out, 0, 255, out=out)

    return out.astype(np.uint8)


def gradient_basic(
    image: np.ndarray,
    structure: Union[np.ndarray, StructuringElement] = None,
    out: Optional[np.ndarray] = None
) -> np.ndarray:
    if structure is None:
        structure = create_rect((3, 3))

    dilated = dilate(image, structure)
    eroded = erode(image, structure)

    if out is None:
        out = np.empty_like(image)

    np.subtract(dilated.astype(np.int32), eroded.astype(np.int32), out=out.astype(np.int32))
    np.clip(out, 0, 255, out=out)

    return out.astype(np.uint8)


def laplacian_gradient(
    image: np.ndarray,
    structure: Union[np.ndarray, StructuringElement] = None,
    out: Optional[np.ndarray] = None
) -> np.ndarray:
    if structure is None:
        structure = create_rect((3, 3))

    dilated = dilate(image, structure)
    eroded = erode(image, structure)

    if out is None:
        out = np.empty_like(image)

    img_int = image.astype(np.int32)
    dilated_int = dilated.astype(np.int32)
    eroded_int = eroded.astype(np.int32)

    laplacian = dilated_int + eroded_int - 2 * img_int
    np.abs(laplacian, out=out.astype(np.int32))
    np.clip(out, 0, 255, out=out)

    return out.astype(np.uint8)


def multi_scale_gradient(
    image: np.ndarray,
    sizes: list = None,
    out: Optional[np.ndarray] = None
) -> np.ndarray:
    if sizes is None:
        sizes = [3, 5, 7]

    gradients = []
    for size in sizes:
        se = create_rect((size, size))
        grad = gradient_basic(image, se)
        gradients.append(grad)

    if out is None:
        out = np.zeros_like(image)

    np.maximum.reduce(gradients, out=out)
    return out


def directional_gradient(
    image: np.ndarray,
    direction: str = 'horizontal',
    structure: Union[np.ndarray, StructuringElement] = None,
    out: Optional[np.ndarray] = None
) -> np.ndarray:
    if direction == 'horizontal':
        se_h = create_rect((1, 3))
        return gradient_basic(image, se_h, out)
    elif direction == 'vertical':
        se_v = create_rect((3, 1))
        return gradient_basic(image, se_v, out)
    elif direction == 'diagonal1':
        se_d1 = np.array([
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, 1]
        ], dtype=np.uint8)
        return gradient_basic(image, se_d1, out)
    elif direction == 'diagonal2':
        se_d2 = np.array([
            [0, 0, 1],
            [0, 1, 0],
            [1, 0, 0]
        ], dtype=np.uint8)
        return gradient_basic(image, se_d2, out)
    else:
        raise ValueError(f"Unknown direction: {direction}")


def sobel_like_gradient(
    image: np.ndarray,
    out: Optional[np.ndarray] = None
) -> np.ndarray:
    grad_h = directional_gradient(image, 'horizontal')
    grad_v = directional_gradient(image, 'vertical')

    if out is None:
        out = np.empty_like(image)

    h_int = grad_h.astype(np.int32)
    v_int = grad_v.astype(np.int32)
    magnitude = np.sqrt(h_int ** 2 + v_int ** 2).astype(np.int32)
    np.clip(magnitude, 0, 255, out=out.astype(np.int32))

    return out.astype(np.uint8)


def edge_detection(
    image: np.ndarray,
    method: str = 'basic',
    threshold: int = 30,
    structure: Union[np.ndarray, StructuringElement] = None,
    out: Optional[np.ndarray] = None
) -> np.ndarray:
    methods = {
        'basic': gradient_basic,
        'internal': gradient_internal,
        'external': gradient_external,
        'laplacian': laplacian_gradient,
        'sobel': sobel_like_gradient
    }

    if method not in methods:
        raise ValueError(f"Unknown method: {method}. Available: {list(methods.keys())}")

    grad = methods[method](image, structure)

    if out is None:
        out = np.empty_like(image)

    out[:] = (grad > threshold).astype(np.uint8) * 255
    return out


def edge_thinning(
    image: np.ndarray,
    out: Optional[np.ndarray] = None
) -> np.ndarray:
    if len(image.shape) != 2:
        raise ValueError("Edge thinning only supports 2D images")

    binary = (image > 127).astype(np.uint8)

    if out is None:
        out = np.zeros_like(image)

    se = create_rect((3, 3))
    prev = np.zeros_like(binary.shape)

    while True:
        eroded = erode(binary, se)
        opened = open_op(binary, se)
        skel = binary - opened

        out = out | skel
        binary = eroded

        if np.sum(binary) == 0:
            break

    return out


def hysteresis_threshold(
    gradient: np.ndarray,
    low_threshold: int = 30,
    high_threshold: int = 80,
    structure: Union[np.ndarray, StructuringElement] = None
) -> np.ndarray:
    if structure is None:
        structure = create_rect((3, 3))

    strong_edges = (gradient >= high_threshold).astype(np.uint8) * 255
    weak_edges = ((gradient >= low_threshold) & (gradient < high_threshold)).astype(np.uint8) * 255

    marker = strong_edges.copy()
    mask = ((weak_edges > 0) | (gradient >= low_threshold)).astype(np.uint8) * 255

    from .reconstruction import morphological_reconstruction

    result = morphological_reconstruction(marker, mask, structure)
    return result


def canny_like(
    image: np.ndarray,
    low_threshold: int = 30,
    high_threshold: int = 80,
    smooth_size: int = 3
) -> np.ndarray:
    if len(image.shape) == 3:
        gray = np.mean(image, axis=2).astype(np.uint8)
    else:
        gray = image

    se_smooth = create_rect((smooth_size, smooth_size))
    smoothed = open_op(close_op(gray, se_smooth), se_smooth)

    grad = sobel_like_gradient(smoothed)

    edges = hysteresis_threshold(grad, low_threshold, high_threshold)

    return edges


def gradient_magnitude_direction(
    image: np.ndarray
) -> Tuple[np.ndarray, np.ndarray]:
    grad_h = directional_gradient(image, 'horizontal')
    grad_v = directional_gradient(image, 'vertical')

    h_int = grad_h.astype(np.float32)
    v_int = grad_v.astype(np.float32)

    magnitude = np.sqrt(h_int ** 2 + v_int ** 2)
    magnitude = np.clip(magnitude, 0, 255).astype(np.uint8)

    direction = np.arctan2(v_int, h_int) * 180 / np.pi

    return magnitude, direction


def non_maximum_suppression(
    magnitude: np.ndarray,
    direction: np.ndarray,
    out: Optional[np.ndarray] = None
) -> np.ndarray:
    if out is None:
        out = np.zeros_like(magnitude)

    height, width = magnitude.shape

    for y in range(1, height - 1):
        for x in range(1, width - 1):
            angle = direction[y, x]

            if (0 <= angle < 22.5) or (157.5 <= angle <= 180) or (-22.5 <= angle < 0) or (-180 <= angle < -157.5):
                neighbors = [magnitude[y, x-1], magnitude[y, x+1]]
            elif (22.5 <= angle < 67.5) or (-157.5 <= angle < -112.5):
                neighbors = [magnitude[y-1, x+1], magnitude[y+1, x-1]]
            elif (67.5 <= angle < 112.5) or (-112.5 <= angle < -67.5):
                neighbors = [magnitude[y-1, x], magnitude[y+1, x]]
            else:
                neighbors = [magnitude[y-1, x-1], magnitude[y+1, x+1]]

            if magnitude[y, x] >= max(neighbors):
                out[y, x] = magnitude[y, x]

    return out
