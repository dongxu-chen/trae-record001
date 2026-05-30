import re
from collections import defaultdict, Counter
from datetime import datetime
from app.redis_client import get_redis


class SlowLogAnalyzer:
    def __init__(self):
        self.redis = get_redis()
        self._init_normalization_rules()
    
    def get_slow_logs(self, count=1000):
        logs = self.redis.execute_command('SLOWLOG GET', count)
        parsed_logs = []
        
        for log in logs:
            log_id, timestamp, duration, command, *extra = log
            parsed_logs.append({
                'id': log_id,
                'timestamp': timestamp,
                'datetime': datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S'),
                'duration_ms': duration / 1000,
                'command': ' '.join(command) if isinstance(command, list) else str(command),
                'command_parts': command if isinstance(command, list) else [str(command)],
                'client_ip': extra[0] if len(extra) > 0 else None,
                'client_name': extra[1] if len(extra) > 1 else None
            })
        
        return parsed_logs
    
    def parse_command(self, command_str):
        parts = command_str.split()
        if not parts:
            return None, None, []
        
        cmd = parts[0].upper()
        key = parts[1] if len(parts) > 1 else None
        args = parts[2:] if len(parts) > 2 else []
        
        return cmd, key, args
    
    def _init_normalization_rules(self):
        self.normalization_rules = {
            'GET': lambda parts: self._normalize_single_key(parts, 'GET'),
            'SET': lambda parts: self._normalize_kv(parts, 'SET'),
            'SETEX': lambda parts: self._normalize_with_ttl(parts, 'SETEX'),
            'SETNX': lambda parts: self._normalize_kv(parts, 'SETNX'),
            'GETSET': lambda parts: self._normalize_kv(parts, 'GETSET'),
            'MGET': lambda parts: self._normalize_multi_key(parts, 'MGET'),
            'MSET': lambda parts: self._normalize_multi_kv(parts, 'MSET'),
            'DEL': lambda parts: self._normalize_multi_key(parts, 'DEL'),
            'EXISTS': lambda parts: self._normalize_multi_key(parts, 'EXISTS'),
            'EXPIRE': lambda parts: self._normalize_with_ttl(parts, 'EXPIRE'),
            'TTL': lambda parts: self._normalize_single_key(parts, 'TTL'),
            'TYPE': lambda parts: self._normalize_single_key(parts, 'TYPE'),
            'RENAME': lambda parts: self._normalize_two_keys(parts, 'RENAME'),
            'HGET': lambda parts: self._normalize_key_field(parts, 'HGET'),
            'HSET': lambda parts: self._normalize_key_field_value(parts, 'HSET'),
            'HGETALL': lambda parts: self._normalize_single_key(parts, 'HGETALL'),
            'HMGET': lambda parts: self._normalize_multi_field(parts, 'HMGET'),
            'HMSET': lambda parts: self._normalize_multi_kv_field(parts, 'HMSET'),
            'HDEL': lambda parts: self._normalize_multi_field(parts, 'HDEL'),
            'HLEN': lambda parts: self._normalize_single_key(parts, 'HLEN'),
            'HKEYS': lambda parts: self._normalize_single_key(parts, 'HKEYS'),
            'HVALS': lambda parts: self._normalize_single_key(parts, 'HVALS'),
            'HINCRBY': lambda parts: self._normalize_key_field_value(parts, 'HINCRBY'),
            'LINDEX': lambda parts: self._normalize_key_index(parts, 'LINDEX'),
            'LINSERT': lambda parts: self._normalize_list_insert(parts, 'LINSERT'),
            'LLEN': lambda parts: self._normalize_single_key(parts, 'LLEN'),
            'LPOP': lambda parts: self._normalize_single_key(parts, 'LPOP'),
            'RPOP': lambda parts: self._normalize_single_key(parts, 'RPOP'),
            'LPUSH': lambda parts: self._normalize_list_push(parts, 'LPUSH'),
            'RPUSH': lambda parts: self._normalize_list_push(parts, 'RPUSH'),
            'LRANGE': lambda parts: self._normalize_key_start_stop(parts, 'LRANGE'),
            'LREM': lambda parts: self._normalize_list_remove(parts, 'LREM'),
            'LSET': lambda parts: self._normalize_key_index_value(parts, 'LSET'),
            'LTRIM': lambda parts: self._normalize_key_start_stop(parts, 'LTRIM'),
            'SADD': lambda parts: self._normalize_multi_member(parts, 'SADD'),
            'SCARD': lambda parts: self._normalize_single_key(parts, 'SCARD'),
            'SISMEMBER': lambda parts: self._normalize_key_member(parts, 'SISMEMBER'),
            'SMEMBERS': lambda parts: self._normalize_single_key(parts, 'SMEMBERS'),
            'SREM': lambda parts: self._normalize_multi_member(parts, 'SREM'),
            'SPOP': lambda parts: self._normalize_key_count(parts, 'SPOP'),
            'SRANDMEMBER': lambda parts: self._normalize_key_count(parts, 'SRANDMEMBER'),
            'ZADD': lambda parts: self._normalize_zset_add(parts, 'ZADD'),
            'ZCARD': lambda parts: self._normalize_single_key(parts, 'ZCARD'),
            'ZCOUNT': lambda parts: self._normalize_key_min_max(parts, 'ZCOUNT'),
            'ZINCRBY': lambda parts: self._normalize_zset_incr(parts, 'ZINCRBY'),
            'ZRANGE': lambda parts: self._normalize_key_start_stop(parts, 'ZRANGE'),
            'ZREVRANGE': lambda parts: self._normalize_key_start_stop(parts, 'ZREVRANGE'),
            'ZRANGEBYSCORE': lambda parts: self._normalize_key_min_max(parts, 'ZRANGEBYSCORE'),
            'ZREVRANGEBYSCORE': lambda parts: self._normalize_key_min_max(parts, 'ZREVRANGEBYSCORE'),
            'ZRANK': lambda parts: self._normalize_key_member(parts, 'ZRANK'),
            'ZREVRANK': lambda parts: self._normalize_key_member(parts, 'ZREVRANK'),
            'ZREM': lambda parts: self._normalize_multi_member(parts, 'ZREM'),
            'ZSCORE': lambda parts: self._normalize_key_member(parts, 'ZSCORE'),
            'INCR': lambda parts: self._normalize_single_key(parts, 'INCR'),
            'INCRBY': lambda parts: self._normalize_key_value(parts, 'INCRBY'),
            'DECR': lambda parts: self._normalize_single_key(parts, 'DECR'),
            'DECRBY': lambda parts: self._normalize_key_value(parts, 'DECRBY'),
            'APPEND': lambda parts: self._normalize_kv(parts, 'APPEND'),
            'STRLEN': lambda parts: self._normalize_single_key(parts, 'STRLEN'),
            'BITCOUNT': lambda parts: self._normalize_key_range(parts, 'BITCOUNT'),
            'BITOP': lambda parts: self._normalize_bitop(parts, 'BITOP'),
            'PFADD': lambda parts: self._normalize_multi_member(parts, 'PFADD'),
            'PFCOUNT': lambda parts: self._normalize_multi_key(parts, 'PFCOUNT'),
            'PFMERGE': lambda parts: self._normalize_multi_key(parts, 'PFMERGE'),
            'GEOADD': lambda parts: self._normalize_geo_add(parts, 'GEOADD'),
            'GEODIST': lambda parts: self._normalize_geo_dist(parts, 'GEODIST'),
            'GEOPOS': lambda parts: self._normalize_multi_member(parts, 'GEOPOS'),
            'KEYS': lambda parts: 'KEYS ?',
            'SCAN': lambda parts: 'SCAN ? [MATCH ?] [COUNT ?]',
            'SSCAN': lambda parts: self._normalize_scan_variant(parts, 'SSCAN'),
            'HSCAN': lambda parts: self._normalize_scan_variant(parts, 'HSCAN'),
            'ZSCAN': lambda parts: self._normalize_scan_variant(parts, 'ZSCAN'),
            'XADD': lambda parts: self._normalize_stream_add(parts, 'XADD'),
            'XREAD': lambda parts: 'XREAD [COUNT ?] [BLOCK ?] STREAMS ? ?',
            'XRANGE': lambda parts: self._normalize_key_start_stop(parts, 'XRANGE'),
            'XREVRANGE': lambda parts: self._normalize_key_start_stop(parts, 'XREVRANGE'),
            'XLEN': lambda parts: self._normalize_single_key(parts, 'XLEN'),
        }
        
        self.large_key_thresholds = {
            'string': {'elements': 1, 'size': 10 * 1024 * 1024},
            'hash': {'elements': 1000, 'size': 5 * 1024 * 1024},
            'list': {'elements': 10000, 'size': 10 * 1024 * 1024},
            'set': {'elements': 5000, 'size': 5 * 1024 * 1024},
            'zset': {'elements': 5000, 'size': 5 * 1024 * 1024},
            'stream': {'elements': 10000, 'size': 10 * 1024 * 1024},
        }
    
    def _normalize_single_key(self, parts, cmd):
        if len(parts) >= 1:
            return f'{cmd} ?'
        return cmd
    
    def _normalize_kv(self, parts, cmd):
        if len(parts) >= 2:
            return f'{cmd} ? ?'
        return cmd
    
    def _normalize_key_value(self, parts, cmd):
        if len(parts) >= 2:
            return f'{cmd} ? ?'
        return cmd
    
    def _normalize_with_ttl(self, parts, cmd):
        if len(parts) >= 3:
            return f'{cmd} ? ?'
        return cmd
    
    def _normalize_two_keys(self, parts, cmd):
        if len(parts) >= 3:
            return f'{cmd} ? ?'
        return cmd
    
    def _normalize_multi_key(self, parts, cmd):
        if len(parts) >= 2:
            return f'{cmd} ?*'
        return cmd
    
    def _normalize_multi_kv(self, parts, cmd):
        if len(parts) >= 2:
            return f'{cmd} ?*'
        return cmd
    
    def _normalize_key_field(self, parts, cmd):
        if len(parts) >= 3:
            return f'{cmd} ? ?'
        return cmd
    
    def _normalize_key_field_value(self, parts, cmd):
        if len(parts) >= 4:
            return f'{cmd} ? ? ?'
        return cmd
    
    def _normalize_multi_field(self, parts, cmd):
        if len(parts) >= 3:
            return f'{cmd} ? ?*'
        return cmd
    
    def _normalize_multi_kv_field(self, parts, cmd):
        if len(parts) >= 3:
            return f'{cmd} ? ?*'
        return cmd
    
    def _normalize_key_index(self, parts, cmd):
        if len(parts) >= 3:
            return f'{cmd} ? ?'
        return cmd
    
    def _normalize_key_index_value(self, parts, cmd):
        if len(parts) >= 4:
            return f'{cmd} ? ? ?'
        return cmd
    
    def _normalize_list_push(self, parts, cmd):
        if len(parts) >= 3:
            return f'{cmd} ? ?*'
        return cmd
    
    def _normalize_list_insert(self, parts, cmd):
        if len(parts) >= 5:
            return f'{cmd} ? ? ? ?'
        return cmd
    
    def _normalize_list_remove(self, parts, cmd):
        if len(parts) >= 4:
            return f'{cmd} ? ? ?'
        return cmd
    
    def _normalize_key_start_stop(self, parts, cmd):
        if len(parts) >= 4:
            return f'{cmd} ? ? ?'
        return cmd
    
    def _normalize_multi_member(self, parts, cmd):
        if len(parts) >= 3:
            return f'{cmd} ? ?*'
        return cmd
    
    def _normalize_key_member(self, parts, cmd):
        if len(parts) >= 3:
            return f'{cmd} ? ?'
        return cmd
    
    def _normalize_key_count(self, parts, cmd):
        if len(parts) >= 3:
            return f'{cmd} ? ?'
        elif len(parts) >= 2:
            return f'{cmd} ?'
        return cmd
    
    def _normalize_zset_add(self, parts, cmd):
        if len(parts) >= 4:
            return f'{cmd} ? ?*'
        return cmd
    
    def _normalize_key_min_max(self, parts, cmd):
        if len(parts) >= 4:
            return f'{cmd} ? ? ?'
        return cmd
    
    def _normalize_zset_incr(self, parts, cmd):
        if len(parts) >= 4:
            return f'{cmd} ? ? ?'
        return cmd
    
    def _normalize_key_range(self, parts, cmd):
        if len(parts) >= 4:
            return f'{cmd} ? ? ?'
        elif len(parts) >= 2:
            return f'{cmd} ?'
        return cmd
    
    def _normalize_bitop(self, parts, cmd):
        if len(parts) >= 4:
            return f'{cmd} ? ? ?*'
        return cmd
    
    def _normalize_geo_add(self, parts, cmd):
        if len(parts) >= 5:
            return f'{cmd} ? ?*'
        return cmd
    
    def _normalize_geo_dist(self, parts, cmd):
        if len(parts) >= 4:
            return f'{cmd} ? ? ? [?]'
        return cmd
    
    def _normalize_scan_variant(self, parts, cmd):
        if len(parts) >= 2:
            return f'{cmd} ? [MATCH ?] [COUNT ?]'
        return cmd
    
    def _normalize_stream_add(self, parts, cmd):
        if len(parts) >= 4:
            return f'{cmd} ? ? ?*'
        return cmd
    
    def normalize_command(self, command_parts):
        if not command_parts:
            return 'UNKNOWN'
        
        cmd = command_parts[0].upper()
        
        if cmd in self.normalization_rules:
            try:
                return self.normalization_rules[cmd](command_parts)
            except Exception:
                return f'{cmd} ?*'
        
        if len(command_parts) == 1:
            return cmd
        elif len(command_parts) == 2:
            return f'{cmd} ?'
        else:
            return f'{cmd} ?*'
    
    def get_slow_log_config(self):
        slowlog_log_slower_than = self.redis.config_get('slowlog-log-slower-than')
        slowlog_max_len = self.redis.config_get('slowlog-max-len')
        
        return {
            'slowlog_log_slower_than': int(slowlog_log_slower_than.get('slowlog-log-slower-than', 0)),
            'slowlog_max_len': int(slowlog_max_len.get('slowlog-max-len', 0))
        }
    
    def analyze_command_patterns(self, logs, normalize=True):
        command_stats = defaultdict(lambda: {
            'count': 0,
            'total_time': 0,
            'avg_time': 0,
            'max_time': 0,
            'min_time': float('inf'),
            'base_command': '',
            'sample_commands': []
        })
        
        for log in logs:
            if log['command_parts']:
                if normalize:
                    normalized_cmd = self.normalize_command(log['command_parts'])
                    base_cmd = log['command_parts'][0].upper()
                else:
                    normalized_cmd = log['command_parts'][0].upper()
                    base_cmd = normalized_cmd
            else:
                normalized_cmd = 'UNKNOWN'
                base_cmd = 'UNKNOWN'
            
            duration = log['duration_ms']
            
            stats = command_stats[normalized_cmd]
            stats['count'] += 1
            stats['total_time'] += duration
            stats['max_time'] = max(stats['max_time'], duration)
            stats['min_time'] = min(stats['min_time'], duration)
            stats['base_command'] = base_cmd
            
            if len(stats['sample_commands']) < 5:
                stats['sample_commands'].append(log['command'])
        
        for cmd, stats in command_stats.items():
            stats['avg_time'] = stats['total_time'] / stats['count'] if stats['count'] > 0 else 0
            if stats['min_time'] == float('inf'):
                stats['min_time'] = 0
        
        sorted_commands = sorted(
            command_stats.items(),
            key=lambda x: x[1]['total_time'],
            reverse=True
        )
        
        return [{'command': cmd, **stats} for cmd, stats in sorted_commands]
    
    def find_hot_keys(self, logs, top_n=20):
        key_stats = defaultdict(lambda: {
            'count': 0,
            'total_time': 0,
            'avg_time': 0,
            'commands': set()
        })
        
        for log in logs:
            parts = log['command_parts']
            if len(parts) >= 2:
                key = parts[1]
                cmd = parts[0].upper()
                duration = log['duration_ms']
                
                stats = key_stats[key]
                stats['count'] += 1
                stats['total_time'] += duration
                stats['commands'].add(cmd)
        
        for key, stats in key_stats.items():
            stats['avg_time'] = stats['total_time'] / stats['count'] if stats['count'] > 0 else 0
            stats['commands'] = list(stats['commands'])
        
        sorted_keys = sorted(
            key_stats.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )[:top_n]
        
        return [{'key': key, **stats} for key, stats in sorted_keys]
    
    def find_large_keys(self, scan_count=1000, size_threshold=10240, element_threshold=None, use_composite_score=True):
        large_keys = []
        cursor = 0
        
        while True:
            cursor, keys = self.redis.scan(cursor, count=scan_count)
            
            for key in keys:
                try:
                    key_type = self.redis.type(key)
                    size_info = self._get_key_size(key, key_type)
                    
                    if not size_info:
                        continue
                    
                    size_score = 0
                    element_score = 0
                    size_flag = False
                    element_flag = False
                    
                    if element_threshold is None:
                        element_threshold = self.large_key_thresholds.get(
                            key_type, {}
                        ).get('elements', 1000)
                    
                    type_size_threshold = self.large_key_thresholds.get(
                        key_type, {}
                    ).get('size', size_threshold)
                    
                    if size_info['total_size'] >= size_threshold:
                        size_flag = True
                        size_score = min(size_info['total_size'] / max(type_size_threshold, 1), 10)
                    
                    if size_info['elements'] >= element_threshold:
                        element_flag = True
                        element_score = min(size_info['elements'] / max(element_threshold, 1), 10)
                    
                    if use_composite_score:
                        composite_score = (size_score * 0.6) + (element_score * 0.4)
                    else:
                        composite_score = max(size_score, element_score)
                    
                    size_ratio = size_info['total_size'] / max(type_size_threshold, 1)
                    element_ratio = size_info['elements'] / max(element_threshold, 1)
                    
                    risk_level = self._assess_risk_level(size_ratio, element_ratio, key_type)
                    
                    if size_flag or element_flag:
                        large_keys.append({
                            'key': key,
                            'type': key_type,
                            **size_info,
                            'size_exceeded': size_flag,
                            'element_exceeded': element_flag,
                            'size_threshold': type_size_threshold,
                            'element_threshold': element_threshold,
                            'size_ratio': round(size_ratio, 2),
                            'element_ratio': round(element_ratio, 2),
                            'size_score': round(size_score, 2),
                            'element_score': round(element_score, 2),
                            'composite_score': round(composite_score, 2),
                            'risk_level': risk_level
                        })
                except Exception:
                    continue
            
            if cursor == 0:
                break
        
        large_keys.sort(key=lambda x: x['composite_score'], reverse=True)
        return large_keys
    
    def _assess_risk_level(self, size_ratio, element_ratio, key_type):
        max_ratio = max(size_ratio, element_ratio)
        
        if max_ratio >= 5 or (size_ratio >= 3 and element_ratio >= 3):
            return 'critical'
        elif max_ratio >= 2 or (size_ratio >= 1.5 and element_ratio >= 1.5):
            return 'high'
        elif max_ratio >= 1:
            return 'medium'
        elif max_ratio >= 0.5:
            return 'low'
        else:
            return 'normal'
    
    def _get_key_size(self, key, key_type):
        try:
            if key_type == 'string':
                size = self.redis.strlen(key)
                return {'total_size': size, 'elements': 1, 'serialized_length': size}
            
            elif key_type == 'list':
                length = self.redis.llen(key)
                size = self.redis.debug_object(key).get('serializedlength', 0)
                return {'total_size': size, 'elements': length, 'serialized_length': size}
            
            elif key_type == 'hash':
                length = self.redis.hlen(key)
                size = self.redis.debug_object(key).get('serializedlength', 0)
                return {'total_size': size, 'elements': length, 'serialized_length': size}
            
            elif key_type == 'set':
                length = self.redis.scard(key)
                size = self.redis.debug_object(key).get('serializedlength', 0)
                return {'total_size': size, 'elements': length, 'serialized_length': size}
            
            elif key_type == 'zset':
                length = self.redis.zcard(key)
                size = self.redis.debug_object(key).get('serializedlength', 0)
                return {'total_size': size, 'elements': length, 'serialized_length': size}
            
            else:
                size = self.redis.debug_object(key).get('serializedlength', 0)
                return {'total_size': size, 'elements': 0, 'serialized_length': size}
        except Exception:
            return None
    
    def get_slow_queries_ranking(self, logs, top_n=20, sort_by='duration'):
        if sort_by == 'duration':
            sorted_logs = sorted(logs, key=lambda x: x['duration_ms'], reverse=True)
        elif sort_by == 'count':
            cmd_count = Counter(log['command_parts'][0] for log in logs if log['command_parts'])
            sorted_logs = sorted(logs, key=lambda x: cmd_count.get(x['command_parts'][0], 0), reverse=True)
        else:
            sorted_logs = logs
        
        return sorted_logs[:top_n]
