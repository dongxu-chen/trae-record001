import time
import json
import requests
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from requests.exceptions import (
    RequestException, Timeout, ConnectionError, SSLError,
    TooManyRedirects, InvalidURL
)
from config import DEFAULT_CONFIG


@dataclass
class RequestResult:
    url: str
    method: str
    params: Dict[str, Any]
    status_code: Optional[int] = None
    response_time: float = 0.0
    response_body: Any = None
    response_headers: Dict[str, str] = field(default_factory=dict)
    error: Optional[str] = None
    error_type: Optional[str] = None
    request_headers: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'url': self.url,
            'method': self.method,
            'params': self.params,
            'status_code': self.status_code,
            'response_time': self.response_time,
            'response_body': self.response_body,
            'response_headers': dict(self.response_headers),
            'error': self.error,
            'error_type': self.error_type,
            'request_headers': self.request_headers,
            'timestamp': self.timestamp
        }


class RequestSender:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = {**DEFAULT_CONFIG, **(config or {})}
        self.session = requests.Session()
        self.last_request_time = 0.0
    
    def _apply_delay(self) -> None:
        delay = self.config.get('delay_between_requests', 0.1)
        if delay > 0:
            elapsed = time.time() - self.last_request_time
            if elapsed < delay:
                time.sleep(delay - elapsed)
        self.last_request_time = time.time()
    
    def _build_url(self, base_url: str, path_params: Dict[str, Any]) -> str:
        url = base_url
        for key, value in path_params.items():
            placeholder = f"{{{key}}}"
            if placeholder in url:
                url = url.replace(placeholder, str(value))
        return url
    
    def _parse_response(self, response: requests.Response) -> Any:
        content_type = response.headers.get('Content-Type', '')
        
        if 'application/json' in content_type:
            try:
                return response.json()
            except json.JSONDecodeError:
                return response.text
        
        if 'text/' in content_type:
            return response.text
        
        try:
            return response.json()
        except json.JSONDecodeError:
            return response.text
    
    def send_request(
        self,
        url: str,
        method: str = 'GET',
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Dict[str, Any]] = None,
        path_params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None
    ) -> RequestResult:
        method = method.upper()
        params = params or {}
        headers = headers or {}
        body = body or {}
        path_params = path_params or {}
        timeout = timeout or self.config.get('timeout', 10)
        max_retries = max_retries or self.config.get('max_retries', 2)
        
        full_url = self._build_url(url, path_params)
        
        result = RequestResult(
            url=full_url,
            method=method,
            params=params if method == 'GET' else body,
            request_headers=headers.copy()
        )
        
        last_error = None
        last_error_type = None
        
        for attempt in range(max_retries + 1):
            try:
                self._apply_delay()
                
                start_time = time.time()
                
                request_args = {
                    'url': full_url,
                    'headers': headers,
                    'timeout': timeout,
                    'allow_redirects': True,
                    'verify': True
                }
                
                if method == 'GET':
                    request_args['params'] = params
                elif method in ('POST', 'PUT', 'PATCH'):
                    content_type = headers.get('Content-Type', 'application/json')
                    if 'application/json' in content_type:
                        request_args['json'] = body
                    elif 'application/x-www-form-urlencoded' in content_type:
                        request_args['data'] = body
                    else:
                        request_args['data'] = body
                
                response = self.session.request(method, **request_args)
                
                result.response_time = (time.time() - start_time) * 1000
                result.status_code = response.status_code
                result.response_headers = dict(response.headers)
                result.response_body = self._parse_response(response)
                result.error = None
                result.error_type = None
                
                return result
                
            except Timeout as e:
                last_error = f"Request timeout after {timeout}s: {str(e)}"
                last_error_type = 'timeout'
            except ConnectionError as e:
                last_error = f"Connection error: {str(e)}"
                last_error_type = 'connection_error'
            except SSLError as e:
                last_error = f"SSL error: {str(e)}"
                last_error_type = 'ssl_error'
                break
            except TooManyRedirects as e:
                last_error = f"Too many redirects: {str(e)}"
                last_error_type = 'too_many_redirects'
                break
            except InvalidURL as e:
                last_error = f"Invalid URL: {str(e)}"
                last_error_type = 'invalid_url'
                break
            except RequestException as e:
                last_error = f"Request error: {str(e)}"
                last_error_type = 'request_error'
            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"
                last_error_type = 'unexpected_error'
            
            if attempt < max_retries:
                time.sleep(0.5 * (attempt + 1))
        
        result.error = last_error
        result.error_type = last_error_type
        result.response_time = 0
        
        return result
    
    def send_batch(
        self,
        requests_list: list
    ) -> list:
        results = []
        for req in requests_list:
            result = self.send_request(**req)
            results.append(result)
        return results
    
    def close(self) -> None:
        self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
