import io
import gc
from PIL import Image, ImageFilter, ImageOps
from PIL.Image import DecompressionBombError
from celery_app import celery
from storage import storage
from webhook_sender import webhook_sender

MAX_IMAGE_PIXELS = 5000 * 5000
CHUNK_SIZE = 128

FILTERS = {
    'grayscale': lambda img: ImageOps.grayscale(img),
    'sepia': lambda img: _apply_sepia(img),
    'blur': lambda img: img.filter(ImageFilter.GaussianBlur(radius=2)),
    'contour': lambda img: img.filter(ImageFilter.CONTOUR),
    'detail': lambda img: img.filter(ImageFilter.DETAIL),
    'edge_enhance': lambda img: img.filter(ImageFilter.EDGE_ENHANCE),
    'emboss': lambda img: img.filter(ImageFilter.EMBOSS),
    'find_edges': lambda img: img.filter(ImageFilter.FIND_EDGES),
    'sharpen': lambda img: img.filter(ImageFilter.SHARPEN),
    'smooth': lambda img: img.filter(ImageFilter.SMOOTH),
    'invert': lambda img: ImageOps.invert(img),
    'mirror': lambda img: ImageOps.mirror(img),
    'flip': lambda img: ImageOps.flip(img)
}

def _validate_image_size(image):
    total_pixels = image.width * image.height
    if total_pixels > MAX_IMAGE_PIXELS:
        raise ValueError(
            f'Image too large: {image.width}x{image.height} = {total_pixels} pixels. '
            f'Max allowed: {MAX_IMAGE_PIXELS} pixels'
        )

def _apply_sepia(image):
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    width, height = image.size
    output = Image.new('RGB', (width, height))
    
    for y_start in range(0, height, CHUNK_SIZE):
        y_end = min(y_start + CHUNK_SIZE, height)
        
        for x_start in range(0, width, CHUNK_SIZE):
            x_end = min(x_start + CHUNK_SIZE, width)
            
            box = (x_start, y_start, x_end, y_end)
            chunk = image.crop(box)
            pixels = chunk.load()
            chunk_w, chunk_h = chunk.size
            
            for x in range(chunk_w):
                for y in range(chunk_h):
                    r, g, b = pixels[x, y]
                    
                    tr = int(0.393 * r + 0.769 * g + 0.189 * b)
                    tg = int(0.349 * r + 0.686 * g + 0.168 * b)
                    tb = int(0.272 * r + 0.534 * g + 0.131 * b)
                    
                    tr = min(255, max(0, tr))
                    tg = min(255, max(0, tg))
                    tb = min(255, max(0, tb))
                    
                    pixels[x, y] = (tr, tg, tb)
            
            output.paste(chunk, box)
            del chunk
            gc.collect()
    
    return output

def _get_image_format(image, original_format=None):
    if original_format:
        return original_format.upper()
    
    if image.mode == 'RGBA':
        return 'PNG'
    return 'JPEG'

@celery.task(bind=True, name='tasks.process_thumbnail')
def process_thumbnail(self, image_bytes, width=None, height=None, quality=85, maintain_aspect_ratio=True, webhook_url=None):
    image = None
    result_data = None
    task_id = self.request.id
    
    try:
        webhook_sender.send_task_started(webhook_url, task_id, 'thumbnail')
        
        self.update_state(state='PROCESSING', meta={'step': 'loading_image'})
        
        with Image.open(io.BytesIO(image_bytes)) as img:
            _validate_image_size(img)
            
            original_format = img.format
            original_size = (img.width, img.height)
            
            if img.mode not in ('RGB', 'L', 'RGBA'):
                if img.mode == 'P':
                    img = img.convert('RGBA')
                else:
                    img = img.convert('RGB')
            
            self.update_state(state='PROCESSING', meta={'step': 'resizing'})
            
            target_w = width or img.width
            target_h = height or img.height
            
            if maintain_aspect_ratio:
                ratio = min(target_w / img.width, target_h / img.height)
                new_w = max(1, int(img.width * ratio))
                new_h = max(1, int(img.height * ratio))
                
                if ratio < 1.0:
                    if ratio > 0.5:
                        img.thumbnail((new_w, new_h), Image.Resampling.LANCZOS)
                    else:
                        image = img.resize((new_w, new_h), Image.Resampling.BILINEAR)
                        img = image
            else:
                image = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
                img = image
            
            self.update_state(state='PROCESSING', meta={'step': 'uploading'})
            
            output_format = _get_image_format(img, original_format)
            result = storage.upload_image(img, format=output_format, quality=quality)
            
            final_w, final_h = img.width, img.height
        
        result_data = {
            'status': 'success',
            'task_type': 'thumbnail',
            'result': result,
            'original_dimensions': {
                'width': original_size[0],
                'height': original_size[1]
            },
            'dimensions': {
                'width': final_w,
                'height': final_h
            }
        }
        
        webhook_sender.send_task_completed(webhook_url, task_id, 'thumbnail', result_data)
        
        return result_data
        
    except DecompressionBombError:
        error_msg = 'Image decompression bomb detected - image too large'
        self.update_state(state='FAILURE', meta={'error': error_msg})
        webhook_sender.send_task_failed(webhook_url, task_id, 'thumbnail', error_msg)
        raise ValueError(error_msg)
    except Exception as e:
        error_msg = str(e)
        self.update_state(state='FAILURE', meta={'error': error_msg})
        webhook_sender.send_task_failed(webhook_url, task_id, 'thumbnail', e)
        raise
    finally:
        if image is not None:
            image.close()
            del image
        gc.collect()

@celery.task(bind=True, name='tasks.process_filter')
def process_filter(self, image_bytes, filter_name, quality=85, webhook_url=None):
    processed_img = None
    result_data = None
    task_id = self.request.id
    
    try:
        webhook_sender.send_task_started(webhook_url, task_id, 'filter')
        
        if filter_name not in FILTERS:
            raise ValueError(f'Unknown filter: {filter_name}')
        
        self.update_state(state='PROCESSING', meta={'step': 'loading_image'})
        
        with Image.open(io.BytesIO(image_bytes)) as img:
            _validate_image_size(img)
            
            original_format = img.format
            original_size = (img.width, img.height)
            
            self.update_state(state='PROCESSING', meta={'step': f'applying_{filter_name}'})
            
            filter_func = FILTERS[filter_name]
            
            if filter_name in ['invert'] and img.mode != 'RGB':
                img = img.convert('RGB')
            elif filter_name in ['grayscale', 'sepia']:
                if img.mode not in ('RGB', 'RGBA', 'L'):
                    img = img.convert('RGB')
            
            processed_img = filter_func(img)
            
            self.update_state(state='PROCESSING', meta={'step': 'uploading'})
            
            output_format = _get_image_format(processed_img, original_format)
            result = storage.upload_image(processed_img, format=output_format, quality=quality)
            
            final_w, final_h = processed_img.width, processed_img.height
        
        result_data = {
            'status': 'success',
            'task_type': 'filter',
            'filter': filter_name,
            'result': result,
            'original_dimensions': {
                'width': original_size[0],
                'height': original_size[1]
            },
            'dimensions': {
                'width': final_w,
                'height': final_h
            }
        }
        
        webhook_sender.send_task_completed(webhook_url, task_id, 'filter', result_data)
        
        return result_data
        
    except DecompressionBombError:
        error_msg = 'Image decompression bomb detected - image too large'
        self.update_state(state='FAILURE', meta={'error': error_msg})
        webhook_sender.send_task_failed(webhook_url, task_id, 'filter', error_msg)
        raise ValueError(error_msg)
    except Exception as e:
        error_msg = str(e)
        self.update_state(state='FAILURE', meta={'error': error_msg})
        webhook_sender.send_task_failed(webhook_url, task_id, 'filter', e)
        raise
    finally:
        if processed_img is not None:
            processed_img.close()
            del processed_img
        gc.collect()

@celery.task(bind=True, name='tasks.batch_process')
def batch_process(self, image_bytes, operations, quality=85, webhook_url=None):
    image = None
    result_data = None
    task_id = self.request.id
    
    try:
        webhook_sender.send_task_started(webhook_url, task_id, 'batch')
        
        self.update_state(state='PROCESSING', meta={'step': 'loading_image'})
        
        with Image.open(io.BytesIO(image_bytes)) as img:
            _validate_image_size(img)
            
            original_format = img.format
            original_size = (img.width, img.height)
            
            if img.mode not in ('RGB', 'L', 'RGBA'):
                if img.mode == 'P':
                    img = img.convert('RGBA')
                else:
                    img = img.convert('RGB')
            
            image = img.copy()
        
        total_ops = len(operations)
        temp_imgs = []
        
        try:
            for i, op in enumerate(operations):
                op_type = op.get('type')
                progress = int((i + 1) / total_ops * 100)
                
                if op_type == 'resize':
                    self.update_state(state='PROCESSING', meta={
                        'step': 'resizing',
                        'progress': progress
                    })
                    
                    width = op.get('width')
                    height = op.get('height')
                    maintain_aspect = op.get('maintain_aspect_ratio', True)
                    
                    target_w = width or image.width
                    target_h = height or image.height
                    
                    if maintain_aspect:
                        ratio = min(target_w / image.width, target_h / image.height)
                        new_w = max(1, int(image.width * ratio))
                        new_h = max(1, int(image.height * ratio))
                        
                        if ratio < 1.0:
                            if ratio > 0.5:
                                image.thumbnail((new_w, new_h), Image.Resampling.LANCZOS)
                            else:
                                new_image = image.resize((new_w, new_h), Image.Resampling.BILINEAR)
                                temp_imgs.append(image)
                                image = new_image
                    else:
                        new_image = image.resize((target_w, target_h), Image.Resampling.LANCZOS)
                        temp_imgs.append(image)
                        image = new_image
                
                elif op_type == 'filter':
                    filter_name = op.get('filter')
                    if filter_name not in FILTERS:
                        raise ValueError(f'Unknown filter: {filter_name}')
                    
                    self.update_state(state='PROCESSING', meta={
                        'step': f'applying_{filter_name}',
                        'progress': progress
                    })
                    
                    filter_func = FILTERS[filter_name]
                    
                    if filter_name in ['invert'] and image.mode != 'RGB':
                        new_image = image.convert('RGB')
                        temp_imgs.append(image)
                        image = new_image
                    
                    new_image = filter_func(image)
                    temp_imgs.append(image)
                    image = new_image
            
            self.update_state(state='PROCESSING', meta={'step': 'uploading', 'progress': 95})
            
            output_format = _get_image_format(image, original_format)
            result = storage.upload_image(image, format=output_format, quality=quality)
            
            final_w, final_h = image.width, image.height
        
        finally:
            for temp in temp_imgs:
                temp.close()
                del temp
            temp_imgs = []
            gc.collect()
        
        result_data = {
            'status': 'success',
            'task_type': 'batch',
            'operations': operations,
            'result': result,
            'original_dimensions': {
                'width': original_size[0],
                'height': original_size[1]
            },
            'dimensions': {
                'width': final_w,
                'height': final_h
            }
        }
        
        webhook_sender.send_task_completed(webhook_url, task_id, 'batch', result_data)
        
        return result_data
        
    except DecompressionBombError:
        error_msg = 'Image decompression bomb detected - image too large'
        self.update_state(state='FAILURE', meta={'error': error_msg})
        webhook_sender.send_task_failed(webhook_url, task_id, 'batch', error_msg)
        raise ValueError(error_msg)
    except Exception as e:
        error_msg = str(e)
        self.update_state(state='FAILURE', meta={'error': error_msg})
        webhook_sender.send_task_failed(webhook_url, task_id, 'batch', e)
        raise
    finally:
        if image is not None:
            image.close()
            del image
        gc.collect()

def get_available_filters():
    return list(FILTERS.keys())
