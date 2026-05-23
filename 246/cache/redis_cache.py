import redis
import json
import hashlib
from PIL import Image
import imagehash
from typing import Optional, Dict, List, Tuple
from config import config

class HashType:
    MD5 = "md5"
    PHASH = "phash"
    DHASH = "dhash"
    AHASH = "ahash"

class CacheHitSource:
    NONE = "none"
    MD5 = "md5_exact"
    PHASH = "phash_similar"
    DHASH = "dhash_similar"
    AHASH = "ahash_similar"

class RedisCache:
    def __init__(self):
        self.client = redis.Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            db=config.REDIS_DB,
            password=config.REDIS_PASSWORD,
            decode_responses=True
        )
        self.cache_prefix = "audit:result:"
        self.md5_prefix = "audit:md5:"
        self.phash_prefix = "audit:phash:"
        self.dhash_prefix = "audit:dhash:"
        self.ahash_prefix = "audit:ahash:"
        self.phash_bucket_prefix = "audit:phash_bucket:"
        self.stats_prefix = "audit:stats:"
        
        self.phash_threshold = 5
        self.dhash_threshold = 8
        self.ahash_threshold = 6
    
    def _generate_md5_hash(self, image_data: bytes) -> str:
        return hashlib.md5(image_data).hexdigest()
    
    def _generate_phash(self, image: Image.Image) -> str:
        return str(imagehash.phash(image, hash_size=8))
    
    def _generate_dhash(self, image: Image.Image) -> str:
        return str(imagehash.dhash(image, hash_size=8))
    
    def _generate_ahash(self, image: Image.Image) -> str:
        return str(imagehash.average_hash(image, hash_size=8))
    
    def _get_phash_bucket(self, phash_str: str) -> str:
        return phash_str[:4]
    
    def get_cache_key(self, md5_hash: str) -> str:
        return f"{self.cache_prefix}{md5_hash}"
    
    def get_by_md5(self, image_data: bytes) -> Tuple[Optional[Dict], str]:
        md5_hash = self._generate_md5_hash(image_data)
        cache_key = self.get_cache_key(md5_hash)
        cached = self.client.get(cache_key)
        
        if cached:
            result = json.loads(cached)
            result["cache_hit_source"] = CacheHitSource.MD5
            return result, md5_hash
        return None, md5_hash
    
    def get_by_phash_fast(self, image: Image.Image, md5_hash: str) -> Optional[Dict]:
        target_phash = self._generate_phash(image)
        target_phash_obj = imagehash.hex_to_hash(target_phash)
        bucket = self._get_phash_bucket(target_phash)
        
        bucket_key = f"{self.phash_bucket_prefix}{bucket}"
        bucket_members = self.client.smembers(bucket_key)
        
        best_match = None
        best_distance = float('inf')
        
        for stored_md5 in bucket_members:
            if stored_md5 == md5_hash:
                continue
            
            phash_key = f"{self.phash_prefix}{stored_md5}"
            stored_phash_str = self.client.get(phash_key)
            
            if stored_phash_str:
                stored_phash = imagehash.hex_to_hash(stored_phash_str)
                distance = target_phash_obj - stored_phash
                
                if distance <= self.phash_threshold and distance < best_distance:
                    result_key = self.get_cache_key(stored_md5)
                    cached_result = self.client.get(result_key)
                    if cached_result:
                        best_match = json.loads(cached_result)
                        best_match["cache_hit_source"] = CacheHitSource.PHASH
                        best_match["hash_distance"] = distance
                        best_distance = distance
        
        return best_match
    
    def get_by_dhash(self, image: Image.Image, md5_hash: str) -> Optional[Dict]:
        target_dhash = self._generate_dhash(image)
        target_dhash_obj = imagehash.hex_to_hash(target_dhash)
        
        pattern = f"{self.dhash_prefix}*"
        best_match = None
        best_distance = float('inf')
        
        for key in self.client.scan_iter(pattern, count=100):
            stored_md5 = key.replace(self.dhash_prefix, "")
            if stored_md5 == md5_hash:
                continue
            
            stored_dhash_str = self.client.get(key)
            if stored_dhash_str:
                stored_dhash = imagehash.hex_to_hash(stored_dhash_str)
                distance = target_dhash_obj - stored_dhash
                
                if distance <= self.dhash_threshold and distance < best_distance:
                    result_key = self.get_cache_key(stored_md5)
                    cached_result = self.client.get(result_key)
                    if cached_result:
                        best_match = json.loads(cached_result)
                        best_match["cache_hit_source"] = CacheHitSource.DHASH
                        best_match["hash_distance"] = distance
                        best_distance = distance
        
        return best_match
    
    def get_cached_result(self, image_data: bytes, image: Optional[Image.Image] = None, 
                          use_multi_hash: bool = True) -> Tuple[Optional[Dict], str]:
        md5_result, md5_hash = self.get_by_md5(image_data)
        if md5_result:
            return md5_result, md5_hash
        
        if use_multi_hash and image:
            phash_result = self.get_by_phash_fast(image, md5_hash)
            if phash_result:
                return phash_result, md5_hash
            
            dhash_result = self.get_by_dhash(image, md5_hash)
            if dhash_result:
                return dhash_result, md5_hash
        
        return None, md5_hash
    
    def set_cached_result(self, image_data: bytes, image: Image.Image, result: Dict) -> str:
        md5_hash = self._generate_md5_hash(image_data)
        cache_key = self.get_cache_key(md5_hash)
        
        result["cache_md5"] = md5_hash
        self.client.setex(cache_key, config.CACHE_TTL, json.dumps(result))
        
        phash = self._generate_phash(image)
        phash_key = f"{self.phash_prefix}{md5_hash}"
        self.client.setex(phash_key, config.CACHE_TTL, phash)
        
        bucket = self._get_phash_bucket(phash)
        bucket_key = f"{self.phash_bucket_prefix}{bucket}"
        self.client.sadd(bucket_key, md5_hash)
        self.client.expire(bucket_key, config.CACHE_TTL)
        
        dhash = self._generate_dhash(image)
        dhash_key = f"{self.dhash_prefix}{md5_hash}"
        self.client.setex(dhash_key, config.CACHE_TTL, dhash)
        
        ahash = self._generate_ahash(image)
        ahash_key = f"{self.ahash_prefix}{md5_hash}"
        self.client.setex(ahash_key, config.CACHE_TTL, ahash)
        
        return md5_hash
    
    def cache_with_multi_hash(self, image_data: bytes, image: Image.Image, result: Dict) -> Dict:
        md5_hash = self.set_cached_result(image_data, image, result)
        result["cache_md5"] = md5_hash
        return result
    
    def get_cache_stats(self) -> Dict:
        info = self.client.info()
        
        md5_count = len(list(self.client.scan_iter(f"{self.cache_prefix}*", count=1000)))
        phash_count = len(list(self.client.scan_iter(f"{self.phash_prefix}*", count=1000)))
        bucket_count = len(list(self.client.scan_iter(f"{self.phash_bucket_prefix}*", count=1000)))
        
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        hit_rate = hits / max(hits + misses, 1)
        
        return {
            "total_cached_items": md5_count,
            "phash_indexed": phash_count,
            "phash_buckets": bucket_count,
            "used_memory": info.get("used_memory_human", "0B"),
            "hit_rate": round(hit_rate, 4),
            "total_hits": hits,
            "total_misses": misses
        }
    
    def delete_cache(self, image_data: bytes) -> bool:
        md5_hash = self._generate_md5_hash(image_data)
        cache_key = self.get_cache_key(md5_hash)
        phash_key = f"{self.phash_prefix}{md5_hash}"
        dhash_key = f"{self.dhash_prefix}{md5_hash}"
        ahash_key = f"{self.ahash_prefix}{md5_hash}"
        
        phash_str = self.client.get(phash_key)
        if phash_str:
            bucket = self._get_phash_bucket(phash_str)
            bucket_key = f"{self.phash_bucket_prefix}{bucket}"
            self.client.srem(bucket_key, md5_hash)
        
        deleted = self.client.delete(cache_key, phash_key, dhash_key, ahash_key)
        return deleted > 0
    
    def clear_all_cache(self) -> int:
        patterns = [
            f"{self.cache_prefix}*",
            f"{self.phash_prefix}*",
            f"{self.dhash_prefix}*",
            f"{self.ahash_prefix}*",
            f"{self.phash_bucket_prefix}*"
        ]
        total_deleted = 0
        for pattern in patterns:
            for key in self.client.scan_iter(pattern):
                total_deleted += self.client.delete(key)
        return total_deleted

cache = RedisCache()
