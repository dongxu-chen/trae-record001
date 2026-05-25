#!/usr/bin/env python3
"""
Flowchart image processor using OpenCV + PaddleOCR/tesseract.
- Fuses OCR text boxes with shape contours for precise text-shape matching.
- Detects dual exits from decision nodes and extracts branch labels.
- Builds node-edge graph with arrow connectivity.
"""

import sys
import json
import os
import re

import cv2
import numpy as np

try:
    from paddleocr import PaddleOCR
    PADDLE_AVAILABLE = True
except ImportError:
    PADDLE_AVAILABLE = False

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

NODE_TYPES = {
    'start': 'start',
    'end': 'end',
    'process': 'process',
    'decision': 'decision',
    'input_output': 'input_output',
}

SHAPE_COLORS = {
    'start': (0, 200, 0),
    'end': (200, 0, 0),
    'process': (0, 100, 255),
    'decision': (255, 165, 0),
    'input_output': (128, 0, 255),
}


def preprocess_image(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blurred, 180, 255, cv2.THRESH_BINARY_INV)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=1)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel, iterations=1)
    return gray, thresh, cleaned


def detect_contours(thresh):
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return contours


def classify_shape(cnt, image_shape):
    h, w = image_shape[:2]
    area = cv2.contourArea(cnt)
    min_area = max(100, h * w * 0.002)
    if area < min_area:
        return None, None

    epsilon = 0.02 * cv2.arcLength(cnt, True)
    approx = cv2.approxPolyDP(cnt, epsilon, True)
    x, y, bw, bh = cv2.boundingRect(cnt)
    hull = cv2.convexHull(cnt)
    hull_area = cv2.contourArea(hull)
    aspect = bw / bh if bh > 0 else 1
    rect_area = bw * bh
    extent = area / rect_area if rect_area > 0 else 0
    perimeter = cv2.arcLength(cnt, True)
    circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0

    if circularity > 0.78 and 0.4 < aspect < 2.5:
        return 'oval', (x, y, bw, bh)

    if len(approx) >= 8 and circularity > 0.55 and 0.3 < aspect < 3.0:
        return 'oval', (x, y, bw, bh)

    if len(approx) == 4:
        pts = approx.reshape(4, 2)
        angles = []
        for i in range(4):
            p1 = pts[i]
            p2 = pts[(i + 1) % 4]
            p3 = pts[(i + 2) % 4]
            v1 = p2 - p1
            v2 = p3 - p2
            dot = np.dot(v1, v2)
            norm = np.linalg.norm(v1) * np.linalg.norm(v2)
            angle = np.arccos(np.clip(dot / norm, -1, 1)) * 180 / np.pi if norm > 0 else 90
            angles.append(angle)
        if all(72 < a < 108 for a in angles):
            return 'rectangle', (x, y, bw, bh)
        else:
            if extent < 0.55:
                return 'diamond', (x, y, bw, bh)
            return 'parallelogram', (x, y, bw, bh)

    if len(approx) == 3:
        return 'diamond', (x, y, bw, bh)

    if circularity > 0.55 and 0.3 < aspect < 3.0:
        return 'oval', (x, y, bw, bh)

    return 'unknown', (x, y, bw, bh)


def extract_ocr_boxes(image, ocr_engine):
    text_boxes = []

    if PADDLE_AVAILABLE and ocr_engine:
        try:
            result = ocr_engine.ocr(image, cls=True)
            if result and result[0]:
                for line in result[0]:
                    if not line or len(line) < 2:
                        continue
                    bbox = line[0]
                    text = line[1][0] if len(line[1]) >= 1 else ''
                    conf = line[1][1] if len(line[1]) >= 2 else 0.9
                    if conf < 0.3:
                        continue
                    xs = [pt[0] for pt in bbox]
                    ys = [pt[1] for pt in bbox]
                    x1, y1 = int(min(xs)), int(min(ys))
                    x2, y2 = int(max(xs)), int(max(ys))
                    text_boxes.append({
                        'x': x1,
                        'y': y1,
                        'w': x2 - x1,
                        'h': y2 - y1,
                        'cx': (x1 + x2) // 2,
                        'cy': (y1 + y2) // 2,
                        'text': text.strip(),
                        'conf': conf,
                    })
        except Exception as e:
            print(f"PaddleOCR text box error: {e}", file=sys.stderr)

    if not text_boxes and TESSERACT_AVAILABLE:
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            data = pytesseract.image_to_data(gray, config='--psm 6 -l chi_sim+eng', output_type=pytesseract.Output.DICT)
            for i in range(len(data['text'])):
                text = data['text'][i].strip()
                if not text:
                    continue
                conf = int(data['conf'][i])
                if conf < 30:
                    continue
                x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                text_boxes.append({
                    'x': x,
                    'y': y,
                    'w': w,
                    'h': h,
                    'cx': x + w // 2,
                    'cy': y + h // 2,
                    'text': text,
                    'conf': conf / 100.0,
                })
        except Exception as e:
            print(f"Tesseract text box error: {e}", file=sys.stderr)

    return text_boxes


def fuse_text_with_shapes(shapes, text_boxes, image_shape):
    shape_text = {}
    assigned_texts = set()

    shapes_with_idx = [(i, s) for i, s in enumerate(shapes)]

    for i, shape in shapes_with_idx:
        sx, sy, sw, sh = shape['x'], shape['y'], shape['width'], shape['height']
        scx, scy = sx + sw // 2, sy + sh // 2
        shape_area = sw * sh

        candidates = []
        for ti, tb in enumerate(text_boxes):
            if ti in assigned_texts:
                continue
            tx1, ty1, tw, th = tb['x'], tb['y'], tb['w'], tb['h']
            tx2, ty2 = tx1 + tw, ty1 + th
            tcx, tcy = tb['cx'], tb['cy']

            ix1 = max(sx, tx1)
            iy1 = max(sy, ty1)
            ix2 = min(sx + sw, tx2)
            iy2 = min(sy + sh, ty2)
            iw = max(0, ix2 - ix1)
            ih = max(0, iy2 - iy1)
            intersection = iw * ih
            union = shape_area + tw * th - intersection
            iou = intersection / union if union > 0 else 0

            cx_dist = np.sqrt((scx - tcx) ** 2 + (scy - tcy) ** 2)
            center_in_shape = sx <= tcx <= sx + sw and sy <= tcy <= sy + sh
            shape_center_in_text = tx1 <= scx <= tx2 and ty1 <= scy <= ty2

            score = 0.0
            if iou > 0.05:
                score += iou * 100
            if center_in_shape:
                score += 50
            if shape_center_in_text:
                score += 30
            score += tb['conf'] * 20
            score -= cx_dist * 0.01

            if score > 0:
                candidates.append((score, ti, tb))

        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            best_score, best_ti, best_tb = candidates[0]
            if best_score > 10 or (center_in_shape and best_tb['conf'] > 0.5):
                shape_text[i] = best_tb['text']
                assigned_texts.add(best_ti)

    merged_shapes = []
    for i, shape in enumerate(shapes):
        new_shape = dict(shape)
        new_shape['text'] = shape_text.get(i, shape.get('text', ''))
        merged_shapes.append(new_shape)

    return merged_shapes


def group_nearby_text_boxes(text_boxes, max_distance=15):
    if not text_boxes:
        return text_boxes

    boxes = sorted(text_boxes, key=lambda b: (b['y'], b['x']))
    merged = []
    used = set()

    for i, box in enumerate(boxes):
        if i in used:
            continue
        current = dict(box)
        used.add(i)
        for j in range(i + 1, len(boxes)):
            if j in used:
                continue
            other = boxes[j]
            cy_dist = abs(current['cy'] - other['cy'])
            cx_dist = abs(current['cx'] - other['cx'])
            if cy_dist < max_distance and cx_dist < current['w'] + other['w'] + max_distance:
                x1 = min(current['x'], other['x'])
                y1 = min(current['y'], other['y'])
                x2 = max(current['x'] + current['w'], other['x'] + other['w'])
                y2 = max(current['y'] + current['h'], other['y'] + other['h'])
                current = {
                    'x': x1,
                    'y': y1,
                    'w': x2 - x1,
                    'h': y2 - y1,
                    'cx': (x1 + x2) // 2,
                    'cy': (y1 + y2) // 2,
                    'text': current['text'] + ' ' + other['text'],
                    'conf': (current['conf'] + other['conf']) / 2,
                }
                used.add(j)
        merged.append(current)

    return merged


def detect_arrows_and_labels(image, nodes):
    if len(nodes) < 2:
        return []

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=40,
                            minLineLength=20, maxLineGap=15)

    if lines is None:
        return []

    node_centers = []
    for node in nodes:
        cx = node['x'] + node['width'] // 2
        cy = node['y'] + node['height'] // 2
        node_centers.append((node['id'], cx, cy, node))

    raw_connections = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        line_len = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        if line_len < 15:
            continue

        start_node = _find_nearest_node(x1, y1, node_centers, threshold=60)
        end_node = _find_nearest_node(x2, y2, node_centers, threshold=60)

        if start_node and end_node and start_node != end_node:
            mid_x = (x1 + x2) // 2
            mid_y = (y1 + y2) // 2
            raw_connections.append({
                'from': start_node,
                'to': end_node,
                'mid_x': mid_x,
                'mid_y': mid_y,
                'x1': x1, 'y1': y1,
                'x2': x2, 'y2': y2,
                'label': '',
            })

    deduped = {}
    for conn in raw_connections:
        key = (conn['from'], conn['to'])
        if key not in deduped:
            deduped[key] = conn
        else:
            old = deduped[key]
            old_x = (old['x1'] + old['x2']) // 2
            old_y = (old['y1'] + old['y2']) // 2
            new_x = conn['mid_x']
            new_y = conn['mid_y']
            if abs(new_x - old_x) > 5 or abs(new_y - old_y) > 5:
                pass

    return list(deduped.values())


def extract_arrow_labels(image, connections, text_boxes):
    if not text_boxes:
        for conn in connections:
            conn['label'] = ''
        return connections

    for conn in connections:
        mid_x, mid_y = conn['mid_x'], conn['mid_y']

        best_label = ''
        best_dist = float('inf')

        for tb in text_boxes:
            tcx, tcy = tb['cx'], tb['cy']
            dist = np.sqrt((mid_x - tcx) ** 2 + (mid_y - tcy) ** 2)
            if dist < best_dist and dist < 50:
                text = tb['text'].strip()
                if text and len(text) <= 6:
                    if re.match(r'^(是|否|yes|no|true|false|Y|N|T|F)$', text, re.IGNORECASE):
                        best_dist = dist
                        best_label = text
                    elif text and dist < best_dist:
                        best_dist = dist
                        best_label = text

        conn['label'] = best_label

    return connections


def detect_dual_exits_for_decisions(nodes, connections):
    node_map = {n['id']: n for n in nodes}

    for node in nodes:
        if node['type'] != 'decision':
            continue

        outgoing = [c for c in connections if c['from'] == node['id']]
        if len(outgoing) >= 2:
            yes_conn = None
            no_conn = None
            for c in outgoing:
                label = c.get('label', '').lower()
                if label in ('是', 'yes', 'true', 'y', 't'):
                    yes_conn = c
                elif label in ('否', 'no', 'false', 'n', 'f'):
                    no_conn = c

            if yes_conn is None and outgoing:
                yes_conn = outgoing[0]
            if no_conn is None and len(outgoing) >= 2:
                no_conn = outgoing[1]

            if yes_conn and not yes_conn.get('label'):
                yes_conn['label'] = '是'
            if no_conn and not no_conn.get('label'):
                no_conn['label'] = '否'

    return connections


def _find_nearest_node(px, py, node_centers, threshold=60):
    best = None
    best_dist = float('inf')
    for nid, cx, cy, _node in node_centers:
        dist = np.sqrt((px - cx) ** 2 + (py - cy) ** 2)
        if dist < threshold and dist < best_dist:
            best_dist = dist
            best = nid
    return best


def assign_start_end(nodes):
    if not nodes:
        return

    ovals = [n for n in nodes if n['type'] == 'oval']
    if len(ovals) >= 2:
        top_oval = min(ovals, key=lambda n: n['y'])
        bottom_oval = max(ovals, key=lambda n: n['y'] + n['height'])
        top_oval['type'] = NODE_TYPES['start']
        bottom_oval['type'] = NODE_TYPES['end']
    elif len(ovals) == 1:
        ovals[0]['type'] = NODE_TYPES['start']
        other_nodes = [n for n in nodes if n['id'] != ovals[0]['id']]
        if other_nodes:
            bottom = max(other_nodes, key=lambda n: n['y'] + n['height'])
            if bottom['type'] in ('process', 'unknown'):
                pass
    else:
        top_nodes = sorted(nodes, key=lambda n: (n['y'], n['x']))
        if top_nodes:
            top_nodes[0]['type'] = NODE_TYPES['start']

    for node in nodes:
        if node['type'] == 'rectangle':
            node['type'] = NODE_TYPES['process']
        elif node['type'] == 'diamond':
            node['type'] = NODE_TYPES['decision']
        elif node['type'] == 'parallelogram':
            node['type'] = NODE_TYPES['input_output']
        elif node['type'] == 'triangle':
            node['type'] = NODE_TYPES['decision']
        elif node['type'] == 'unknown':
            node['type'] = NODE_TYPES['process']


def main():
    if len(sys.argv) < 2:
        print(json.dumps({'error': 'No image path provided'}))
        sys.exit(1)

    image_path = sys.argv[1]
    if not os.path.exists(image_path):
        print(json.dumps({'error': f'Image not found: {image_path}'}))
        sys.exit(1)

    image = cv2.imread(image_path)
    if image is None:
        try:
            with open(image_path, 'rb') as f:
                img_array = np.frombuffer(f.read(), dtype=np.uint8)
            image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        except Exception as e:
            print(json.dumps({'error': f'Failed to load image: {e}'}))
            sys.exit(1)

    if image is None:
        print(json.dumps({'error': 'Failed to load image'}))
        sys.exit(1)

    gray, thresh, cleaned = preprocess_image(image)
    contours = detect_contours(cleaned)

    ocr_engine = None
    if PADDLE_AVAILABLE:
        try:
            ocr_engine = PaddleOCR(use_angle_cls=True, lang='ch', show_log=False)
        except Exception as e:
            print(f"PaddleOCR init error: {e}", file=sys.stderr)

    all_text_boxes = extract_ocr_boxes(image, ocr_engine)

    grouped_text_boxes = group_nearby_text_boxes(all_text_boxes, max_distance=12)

    shapes = []
    for cnt in contours:
        shape_type, bbox = classify_shape(cnt, image.shape)
        if shape_type is None or bbox is None:
            continue
        x, y, w, h = bbox
        shapes.append({
            'x': int(x),
            'y': int(y),
            'width': int(w),
            'height': int(h),
            'type': shape_type,
            'text': '',
        })

    merged_shapes = fuse_text_with_shapes(shapes, grouped_text_boxes, image.shape)

    nodes = []
    for i, shape in enumerate(merged_shapes):
        nodes.append({
            'id': f'node_{i}',
            'type': shape['type'],
            'x': shape['x'],
            'y': shape['y'],
            'width': shape['width'],
            'height': shape['height'],
            'text': shape['text'],
            'center': {
                'x': shape['x'] + shape['width'] // 2,
                'y': shape['y'] + shape['height'] // 2,
            },
        })

    nodes.sort(key=lambda n: (n['center']['y'], n['center']['x']))
    for i, node in enumerate(nodes):
        node['id'] = f'node_{i}'

    assign_start_end(nodes)

    connections = detect_arrows_and_labels(image, nodes)
    connections = extract_arrow_labels(image, connections, all_text_boxes)
    connections = detect_dual_exits_for_decisions(nodes, connections)

    edges = []
    if connections:
        for conn in connections:
            edges.append({
                'from': conn['from'],
                'to': conn['to'],
                'label': conn.get('label', ''),
            })
    else:
        _infer_edges_from_position(nodes, edges)

    result = {
        'nodes': nodes,
        'edges': edges,
    }
    print(json.dumps(result, ensure_ascii=False))


def _infer_edges_from_position(nodes, edges):
    sorted_nodes = sorted(nodes, key=lambda n: (n['center']['y'], n['center']['x']))
    for i in range(len(sorted_nodes) - 1):
        src = sorted_nodes[i]
        dst = sorted_nodes[i + 1]
        if src['type'] == 'end' or dst['type'] == 'start':
            continue
        label = ''
        if src['type'] == 'decision':
            label = '是' if i == 0 else '否'
        edges.append({'from': src['id'], 'to': dst['id'], 'label': label})


if __name__ == '__main__':
    main()
