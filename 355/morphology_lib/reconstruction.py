import numpy as np
from typing import Union, Tuple, Optional
from .structuring_element import StructuringElement, create_rect
from .core import dilate, erode


def morphological_reconstruction(
    marker: np.ndarray,
    mask: np.ndarray,
    structure: Union[np.ndarray, StructuringElement] = None,
    max_iter: int = 1000,
    out: Optional[np.ndarray] = None
) -> np.ndarray:
    if structure is None:
        structure = create_rect((3, 3))

    if marker.shape != mask.shape:
        raise ValueError("Marker and mask must have the same shape")

    if out is None:
        out = np.minimum(marker, mask)
    else:
        np.minimum(marker, mask, out=out)

    prev = np.empty_like(out)
    for i in range(max_iter):
        np.copyto(prev, out)
        dilate(out, structure, out=out)
        np.minimum(out, mask, out=out)
        if np.array_equal(out, prev):
            break

    return out


def fill_holes(
    image: np.ndarray,
    structure: Union[np.ndarray, StructuringElement] = None,
    out: Optional[np.ndarray] = None
) -> np.ndarray:
    if len(image.shape) == 2:
        marker = np.zeros_like(image)
        marker[0, :] = image[0, :]
        marker[-1, :] = image[-1, :]
        marker[:, 0] = image[:, 0]
        marker[:, -1] = image[:, -1]

        mask = 255 - image

        reconstructed = morphological_reconstruction(marker, mask, structure)
        result = 255 - reconstructed

        if out is not None:
            out[:] = result
            return out
        return result
    else:
        result = np.empty_like(image)
        for c in range(image.shape[2]):
            result[:, :, c] = fill_holes(image[:, :, c], structure)
        if out is not None:
            out[:] = result
            return out
        return result


def extract_connected_components(
    image: np.ndarray,
    structure: Union[np.ndarray, StructuringElement] = None,
    out: Optional[np.ndarray] = None
) -> Tuple[np.ndarray, int]:
    if len(image.shape) != 2:
        raise ValueError("Connected components only supports 2D grayscale images")

    binary = (image > 127).astype(np.uint8) * 255

    if out is None:
        labels = np.zeros(image.shape, dtype=np.int32)
    else:
        labels = out
        labels.fill(0)

    current_label = 0
    height, width = image.shape

    if structure is None:
        structure = create_rect((3, 3))

    for y in range(height):
        for x in range(width):
            if binary[y, x] > 0 and labels[y, x] == 0:
                current_label += 1
                marker = np.zeros_like(binary)
                marker[y, x] = 255

                component = morphological_reconstruction(marker, binary, structure)
                labels[component > 0] = current_label

    if out is not None:
        return out, current_label
    return labels, current_label


def remove_small_objects(
    image: np.ndarray,
    min_size: int = 100,
    structure: Union[np.ndarray, StructuringElement] = None,
    out: Optional[np.ndarray] = None
) -> np.ndarray:
    labels, num_labels = extract_connected_components(image, structure)

    if out is None:
        result = np.zeros_like(image)
    else:
        result = out
        result.fill(0)

    for label in range(1, num_labels + 1):
        component_size = np.sum(labels == label)
        if component_size >= min_size:
            result[labels == label] = image[labels == label]

    return result


def extract_boundary(
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


def regional_maxima(
    image: np.ndarray,
    connectivity: int = 8,
    out: Optional[np.ndarray] = None
) -> np.ndarray:
    if len(image.shape) != 2:
        raise ValueError("Regional maxima only supports 2D grayscale images")

    if out is None:
        out = np.zeros_like(image, dtype=np.uint8)

    padded = np.pad(image, 1, mode='edge')

    if connectivity == 8:
        neighbors = [
            padded[0:-2, 0:-2], padded[0:-2, 1:-1], padded[0:-2, 2:],
            padded[1:-1, 0:-2],                padded[1:-1, 2:],
            padded[2:, 0:-2],   padded[2:, 1:-1],  padded[2:, 2:]
        ]
    else:
        neighbors = [
            padded[0:-2, 1:-1],
            padded[1:-1, 0:-2], padded[1:-1, 2:],
            padded[2:, 1:-1]
        ]

    max_neighbors = np.max(neighbors, axis=0)
    out[:] = ((image >= max_neighbors) & (image > 0)).astype(np.uint8) * 255

    return out


def h_minima(
    image: np.ndarray,
    h: int = 10,
    structure: Union[np.ndarray, StructuringElement] = None,
    out: Optional[np.ndarray] = None
) -> np.ndarray:
    if structure is None:
        structure = create_rect((3, 3))

    marker = np.clip(image.astype(np.int32) + h, 0, 255).astype(np.uint8)
    result = morphological_reconstruction(marker, image, structure)

    if out is not None:
        out[:] = result
        return out
    return result


def watershed_basins(
    image: np.ndarray,
    markers: np.ndarray,
    structure: Union[np.ndarray, StructuringElement] = None,
    out: Optional[np.ndarray] = None
) -> np.ndarray:
    if structure is None:
        structure = create_rect((3, 3))

    if out is None:
        out = markers.copy()
    else:
        out[:] = markers

    height, width = image.shape[:2]
    unique_markers = np.unique(markers[markers > 0])

    while True:
        prev = out.copy()

        dilated = dilate(out, structure)

        for y in range(height):
            for x in range(width):
                if out[y, x] == 0:
                    neighbors = dilated[max(0, y-1):min(height, y+2),
                                        max(0, x-1):min(width, x+2)]
                    neighbor_labels = np.unique(neighbors[neighbors > 0])
                    if len(neighbor_labels) == 1:
                        out[y, x] = neighbor_labels[0]

        if np.array_equal(out, prev):
            break

    return out
