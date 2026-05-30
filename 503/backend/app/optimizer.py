from collections import defaultdict
from datetime import datetime


class OptimizationAdvisor:
    def __init__(self):
        self.command_optimizations = {
            'KEYS': {
                'issue': '使用KEYS命令扫描全库',
                'severity': 'high',
                'suggestion': '使用SCAN命令替代KEYS，避免阻塞Redis',
                'example': 'SCAN 0 MATCH pattern COUNT 100',
                'commands': [
                    {
                        'description': '使用SCAN迭代遍历',
                        'command': 'SCAN 0 MATCH user:* COUNT 100',
                        'explanation': '分批次遍历，每次100个，不会阻塞Redis'
                    },
                    {
                        'description': 'Python代码示例',
                        'command': '''
for cursor in range(0, 1000000, 100):
    cursor, keys = redis.scan(cursor, match='user:*', count=100)
    process_keys(keys)
    if cursor == 0:
        break''',
                        'explanation': '循环调用直到cursor返回0'
                    }
                ]
            },
            'HGETALL': {
                'issue': '全量获取Hash字段',
                'severity': 'medium',
                'suggestion': '对于大Hash，使用HSCAN分批获取或只获取需要的字段',
                'example': 'HSCAN key 0 COUNT 100 或 HMGET key field1 field2',
                'commands': [
                    {
                        'description': '分批获取Hash字段',
                        'command': 'HSCAN myhash 0 COUNT 100',
                        'explanation': '每次获取100个字段，适用于大Hash'
                    },
                    {
                        'description': '只获取需要的字段',
                        'command': 'HMGET myhash field1 field2 field3',
                        'explanation': '指定字段名，避免全量扫描'
                    }
                ]
            },
            'SMEMBERS': {
                'issue': '全量获取Set成员',
                'severity': 'medium',
                'suggestion': '对于大Set，使用SSCAN分批获取',
                'example': 'SSCAN key 0 COUNT 100',
                'commands': [
                    {
                        'description': '分批获取Set成员',
                        'command': 'SSCAN myset 0 COUNT 100',
                        'explanation': '每次迭代获取100个成员'
                    }
                ]
            },
            'LRANGE': {
                'issue': '大范围List操作',
                'severity': 'medium',
                'suggestion': '限制LRANGE的范围，避免获取整个列表',
                'example': 'LRANGE key 0 99 (获取前100个元素)',
                'commands': [
                    {
                        'description': '获取前100个元素',
                        'command': 'LRANGE mylist 0 99',
                        'explanation': '只获取最新的100条数据'
                    },
                    {
                        'description': '分页获取',
                        'command': 'LRANGE mylist 0 19',
                        'explanation': '每页20条，按需加载'
                    }
                ]
            },
            'ZRANGE': {
                'issue': '大范围Sorted Set操作',
                'severity': 'medium',
                'suggestion': '限制ZRANGE的范围，使用ZSCAN分批获取',
                'example': 'ZRANGE key 0 99 或 ZSCAN key 0 COUNT 100',
                'commands': [
                    {
                        'description': '获取排名前100的元素',
                        'command': 'ZRANGE myzset 0 99 WITHSCORES',
                        'explanation': '只获取前100名及其分数'
                    },
                    {
                        'description': '按分数范围获取',
                        'command': 'ZRANGEBYSCORE myzset 0 100 LIMIT 0 50',
                        'explanation': '获取分数在0-100之间的前50个元素'
                    }
                ]
            },
            'FLUSHDB': {
                'issue': '清空当前数据库',
                'severity': 'high',
                'suggestion': '生产环境避免使用，如需清空请使用UNLINK分批删除',
                'example': '使用批量UNLINK替代FLUSHDB',
                'commands': [
                    {
                        'description': '批量异步删除',
                        'command': '''
for cursor in range(0, 1000000, 1000):
    cursor, keys = redis.scan(cursor, count=1000)
    if keys:
        redis.unlink(*keys)
    if cursor == 0:
        break''',
                        'explanation': 'UNLINK是异步删除，不会阻塞Redis'
                    }
                ]
            },
            'FLUSHALL': {
                'issue': '清空所有数据库',
                'severity': 'critical',
                'suggestion': '生产环境禁止使用',
                'example': 'N/A',
                'commands': []
            }
        }

        self.key_optimization_commands = {
            'hash': {
                'shard': [
                    {
                        'description': '按字段分片Hash',
                        'command': '''
# 将大Hash拆分为小Hash
HSET user:{id}:basic name "John" age 30
HSET user:{id}:profile address "..." settings "..."''',
                        'explanation': '按业务维度拆分，每个小Hash字段数控制在100以内'
                    },
                    {
                        'description': '配置Ziplist优化',
                        'command': '''
# redis.conf 配置
hash-max-ziplist-entries 512
hash-max-ziplist-value 64''',
                        'explanation': '小Hash使用Ziplist编码，节省内存'
                    }
                ],
                'optimize': [
                    {
                        'description': '删除过期字段',
                        'command': 'HDEL myhash expired_field1 expired_field2',
                        'explanation': '定期清理不再使用的字段'
                    }
                ]
            },
            'list': {
                'shard': [
                    {
                        'description': '按时间分片List',
                        'command': '''
# 按天分片存储日志
LPUSH logs:20240101 "log message 1"
LPUSH logs:20240102 "log message 2"''',
                        'explanation': '每天一个List，避免单List过大'
                    },
                    {
                        'description': '使用Stream替代',
                        'command': '''
XADD mystream * message "log message 1" level "info"
# 按范围读取
XRANGE mystream - + COUNT 100''',
                        'explanation': 'Redis Stream适合消息队列和日志存储'
                    }
                ],
                'optimize': [
                    {
                        'description': '修剪List长度',
                        'command': 'LTRIM mylist 0 999',
                        'explanation': '只保留最新的1000条元素'
                    }
                ]
            },
            'set': {
                'shard': [
                    {
                        'description': '按Hash分片Set',
                        'command': '''
# 按用户ID取模分片
SADD friends:{user_id % 16} friend_id''',
                        'explanation': '分散到16个小Set中'
                    },
                    {
                        'description': '使用Hash替代Set(当值为整数时)',
                        'command': '''
# 用Hash的field存储，value设为1
HSET myset_tag member1 1 member2 1
# 检查是否存在
HEXISTS myset_tag member1''',
                        'explanation': '小集合使用Hash更节省内存'
                    }
                ],
                'optimize': [
                    {
                        'description': '求交集时使用小集合驱动',
                        'command': 'SINTER small_set large_set',
                        'explanation': '将小集合放在前面，提高计算效率'
                    }
                ]
            },
            'zset': {
                'shard': [
                    {
                        'description': '按分数范围分片',
                        'command': '''
# 按分数范围拆分
ZADD rankings:0_1000 500 "user1" 800 "user2"
ZADD rankings:1000_2000 1500 "user3"''',
                        'explanation': '每个Sorted Set只包含一定分数范围的元素'
                    }
                ],
                'optimize': [
                    {
                        'description': '移除低排名元素',
                        'command': 'ZREMRANGEBYRANK myzset 0 -101',
                        'explanation': '只保留前100名，移除其余元素'
                    }
                ]
            },
            'string': {
                'shard': [
                    {
                        'description': '大对象拆分存储',
                        'command': '''
# 将大JSON拆分为多个字段存储
SET user:{id}:name "John"
SET user:{id}:email "john@example.com"
SET user:{id}:profile "{...}"''',
                        'explanation': '避免单个String过大，提高读写效率'
                    },
                    {
                        'description': '使用Hash存储对象',
                        'command': '''
HSET user:{id} name "John" email "john@example.com" age 30''',
                        'explanation': '对象属性用Hash存储，节省内存和网络开销'
                    }
                ],
                'optimize': [
                    {
                        'description': '设置合理的过期时间',
                        'command': 'EXPIRE mykey 3600',
                        'explanation': '为临时数据设置TTL，自动清理'
                    }
                ]
            }
        }
        
        self.data_type_recommendations = {
            'counter': {
                'current': ['string'],
                'recommended': 'Hash或专门计数器',
                'reason': '多个计数器可存入Hash减少内存开销',
                'memory_saving': '30-70%'
            },
            'large_hash': {
                'threshold': 1000,
                'recommended': '考虑分片或使用Ziplist优化配置',
                'reason': '大Hash会转为Hashtable，内存开销增大'
            },
            'large_list': {
                'threshold': 10000,
                'recommended': '考虑使用Stream或分片',
                'reason': '大List操作性能下降明显'
            },
            'frequent_access': {
                'threshold': 100,
                'recommended': '考虑添加本地缓存层',
                'reason': '减少Redis访问压力'
            }
        }
    
    def generate_optimization_suggestions(self, command_patterns, hot_keys, large_keys):
        suggestions = {
            'command_optimizations': [],
            'data_type_optimizations': [],
            'sharding_suggestions': [],
            'general_suggestions': []
        }
        
        suggestions['command_optimizations'] = self._analyze_command_optimizations(command_patterns)
        
        suggestions['data_type_optimizations'] = self._analyze_data_type_optimizations(hot_keys, large_keys)
        
        suggestions['sharding_suggestions'] = self._analyze_sharding_suggestions(hot_keys, large_keys)
        
        suggestions['general_suggestions'] = self._generate_general_suggestions(command_patterns, hot_keys, large_keys)
        
        return suggestions
    
    def _analyze_command_optimizations(self, command_patterns):
        optimizations = []
        
        for pattern in command_patterns:
            cmd = pattern['command']
            if cmd in self.command_optimizations:
                opt = self.command_optimizations[cmd]
                optimizations.append({
                    'command': cmd,
                    'count': pattern['count'],
                    'total_time': pattern['total_time'],
                    **opt
                })
        
        return sorted(optimizations, key=lambda x: x['total_time'], reverse=True)
    
    def _analyze_data_type_optimizations(self, hot_keys, large_keys):
        optimizations = []
        
        for key_info in large_keys:
            key = key_info['key']
            key_type = key_info['type']
            elements = key_info.get('elements', 0)
            size = key_info.get('total_size', 0)
            composite_score = key_info.get('composite_score')
            risk_level = key_info.get('risk_level')
            size_exceeded = key_info.get('size_exceeded', False)
            element_exceeded = key_info.get('element_exceeded', False)
            size_threshold = key_info.get('size_threshold')
            element_threshold = key_info.get('element_threshold')
            size_score = key_info.get('size_score')
            element_score = key_info.get('element_score')
            
            base_optimization = {
                'key': key,
                'type': key_type,
                'elements': elements,
                'total_size': size,
                'composite_score': composite_score,
                'risk_level': risk_level,
                'size_exceeded': size_exceeded,
                'element_exceeded': element_exceeded,
                'size_threshold': size_threshold,
                'element_threshold': element_threshold,
                'size_score': size_score,
                'element_score': element_score,
                'severity': risk_level or 'medium'
            }
            
            if risk_level in ['critical', 'high']:
                optimizations.append({
                    **base_optimization,
                    'issue': f'高风险大Key - {risk_level.upper()}',
                    'suggestion': '立即处理！建议拆分此大Key，避免网络和内存阻塞。可考虑分片存储或迁移到其他存储系统。'
                })
            elif risk_level == 'medium':
                if key_type == 'hash' and elements > 1000:
                    optimizations.append({
                        **base_optimization,
                        'issue': '大Hash结构',
                        'suggestion': '考虑开启Hash的Ziplist优化（hash-max-ziplist-entries, hash-max-ziplist-value）或对大Hash进行分片'
                    })
                elif key_type == 'list' and elements > 10000:
                    optimizations.append({
                        **base_optimization,
                        'issue': '大List结构',
                        'suggestion': '考虑使用Redis Stream或对List进行分片存储，定期清理历史数据'
                    })
                elif key_type == 'set' and elements > 5000:
                    optimizations.append({
                        **base_optimization,
                        'issue': '大Set结构',
                        'suggestion': '考虑使用Hash或BitMap替代，或进行分片存储'
                    })
                elif key_type == 'zset' and elements > 5000:
                    optimizations.append({
                        **base_optimization,
                        'issue': '大Sorted Set结构',
                        'suggestion': '考虑对Sorted Set进行分片存储，或使用SkipList优化'
                    })
                else:
                    optimizations.append({
                        **base_optimization,
                        'issue': '中等风险大Key',
                        'suggestion': '建议监控此Key的增长趋势，适时进行清理或优化'
                    })
            elif risk_level == 'low':
                optimizations.append({
                    **base_optimization,
                    'issue': '低风险大Key',
                    'suggestion': '建议关注此Key的增长趋势，定期检查是否需要清理'
                })
        
        for key_info in hot_keys[:10]:
            if key_info['count'] > 500:
                optimizations.append({
                    'key': key_info['key'],
                    'type': 'hot_key',
                    'issue': '高频访问Key',
                    'access_count': key_info['count'],
                    'total_time': key_info['total_time'],
                    'suggestion': '考虑添加本地缓存(如Guava Cache, Caffeine)或进行读写分离',
                    'severity': 'medium',
                    'risk_level': 'medium'
                })
        
        return sorted(optimizations, key=lambda x: x.get('composite_score', 0), reverse=True)
    
    def _analyze_sharding_suggestions(self, hot_keys, large_keys):
        suggestions = []
        
        risk_distribution = {}
        total_composite_score = 0
        large_keys_with_score = 0
        
        for k in large_keys:
            risk = k.get('risk_level', 'unknown')
            risk_distribution[risk] = risk_distribution.get(risk, 0) + 1
            score = k.get('composite_score')
            if score is not None:
                total_composite_score += score
                large_keys_with_score += 1
        
        avg_composite_score = total_composite_score / large_keys_with_score if large_keys_with_score > 0 else None
        
        critical_count = risk_distribution.get('critical', 0)
        high_count = risk_distribution.get('high', 0)
        
        if len(hot_keys) > 50:
            key_patterns = self._extract_key_patterns([k['key'] for k in hot_keys])
            suggestions.append({
                'type': 'hot_key_sharding',
                'issue': '热点Key集中',
                'hot_key_count': len(hot_keys),
                'patterns': key_patterns[:5],
                'suggestion': '建议按照业务维度对热点Key进行分片，分布到不同Redis实例',
                'sharding_strategy': [
                    '按用户ID取模分片: user:{id} -> user:{id%N}',
                    '按业务类型分片: cache:{type}:* -> cache-{type}:*',
                    '一致性哈希分片'
                ]
            })
        
        total_large_size = sum(k.get('total_size', 0) for k in large_keys)
        if len(large_keys) > 0 and (total_large_size > 100 * 1024 * 1024 or critical_count > 0 or high_count >= 3):
            suggestion = {
                'type': 'large_key_sharding',
                'issue': '大Key占用过多内存',
                'total_large_size': total_large_size,
                'large_key_count': len(large_keys),
                'risk_distribution': risk_distribution,
                'suggestion': '建议将大Key拆分后存储到不同Redis实例或使用不同存储方案',
                'alternatives': [
                    'MongoDB存储大文档',
                    'Elasticsearch存储索引数据',
                    '对象存储存储二进制大文件'
                ]
            }
            if avg_composite_score is not None:
                suggestion['avg_composite_score'] = avg_composite_score
            if critical_count > 0:
                suggestion['issue'] = f'存在{critical_count}个严重风险大Key，需立即处理'
            elif high_count >= 3:
                suggestion['issue'] = f'存在{high_count}个高风险大Key，建议处理'
            
            suggestions.append(suggestion)
        
        return suggestions
    
    def _extract_key_patterns(self, keys):
        patterns = defaultdict(int)
        
        for key in keys:
            parts = key.split(':')
            if len(parts) >= 2:
                pattern = ':'.join(parts[:-1]) + ':*'
                patterns[pattern] += 1
        
        return [{'pattern': p, 'count': c} for p, c in sorted(patterns.items(), key=lambda x: x[1], reverse=True)]
    
    def _generate_general_suggestions(self, command_patterns, hot_keys, large_keys):
        suggestions = []
        
        total_commands = sum(p['count'] for p in command_patterns)
        total_time = sum(p['total_time'] for p in command_patterns)
        
        if total_commands > 0:
            avg_time = total_time / total_commands
            if avg_time > 10:
                suggestions.append({
                    'type': 'performance',
                    'issue': f'平均慢查询耗时较高 ({avg_time:.2f}ms)',
                    'suggestion': '建议检查慢查询阈值配置，优化慢命令'
                })
        
        write_commands = ['SET', 'HSET', 'LPUSH', 'RPUSH', 'SADD', 'ZADD', 'INCR', 'DECR']
        write_count = sum(p['count'] for p in command_patterns if p['command'] in write_commands)
        if total_commands > 0 and write_count / total_commands > 0.6:
            suggestions.append({
                'type': 'workload',
                'issue': f'写操作占比较高 ({write_count/total_commands*100:.1f}%)',
                'suggestion': '建议考虑读写分离，使用从节点处理读请求'
            })
        
        if len(large_keys) > 20:
            suggestions.append({
                'type': 'memory',
                'issue': f'存在 {len(large_keys)} 个大Key',
                'suggestion': '建议定期清理过期数据，开启Redis内存淘汰策略'
            })
        
        return suggestions

    def generate_auto_optimization_commands(self, large_keys, hot_keys):
        optimization_commands = []

        for key_info in large_keys:
            key = key_info['key']
            key_type = key_info.get('type', 'string')
            risk_level = key_info.get('risk_level', 'low')
            elements = key_info.get('elements', 0)
            total_size = key_info.get('total_size', 0)

            if key_type in self.key_optimization_commands:
                key_cmds = self.key_optimization_commands[key_type]
                commands = []

                if risk_level in ['critical', 'high']:
                    if 'shard' in key_cmds:
                        commands.extend(key_cmds['shard'])
                if risk_level in ['medium', 'low']:
                    if 'optimize' in key_cmds:
                        commands.extend(key_cmds['optimize'])

                if commands:
                    optimization_commands.append({
                        'key': key,
                        'key_type': key_type,
                        'risk_level': risk_level,
                        'elements': elements,
                        'total_size': total_size,
                        'optimization_commands': commands,
                        'priority': 'critical' if risk_level in ['critical', 'high'] else 'medium'
                    })

        for key_info in hot_keys[:5]:
            key = key_info['key']
            count = key_info.get('count', 0)

            if count > 100:
                optimization_commands.append({
                    'key': key,
                    'key_type': 'hot_key',
                    'risk_level': 'medium',
                    'access_count': count,
                    'optimization_commands': [
                        {
                            'description': '添加本地缓存',
                            'command': '''import cachetools
cache = cachetools.TTLCache(maxsize=1000, ttl=60)

def get_data(key):
    if key in cache:
        return cache[key]
    value = redis.get(key)
    cache[key] = value
    return value''',
                            'explanation': '使用本地缓存减少Redis访问'
                        },
                        {
                            'description': '使用读写分离',
                            'command': '# 读操作走从节点\n# 写操作走主节点',
                            'explanation': '热点Key分散读写压力'
                        }
                    ],
                    'priority': 'medium'
                })

        return sorted(optimization_commands, key=lambda x: (x['priority'] != 'critical', -x.get('elements', 0)))

    def get_executable_scripts(self, optimization_type='all'):
        scripts = {
            'cleanup_expired': '''-- 清理过期Key的Lua脚本
for cursor in 0, 1000 do
  cursor, keys = redis.call('SCAN', cursor, 'COUNT', 100)
  for key in keys do
    ttl = redis.call('TTL', key)
    if ttl == -1 then
      -- 无过期时间，根据业务判断是否删除
    end
  end
  if cursor == 0 then
    break
  end
end''',
            'batch_delete_pattern': '''import redis

def delete_by_pattern(r, pattern):
    for cursor in 0, 1000000, 1000:
        cursor, keys = r.scan(cursor, match=pattern, count=1000)
        if keys:
            r.unlink(*keys)
        if cursor == 0:
            break''',
            'memory_optimize': '''# Redis 内存优化配置建议
# 在 redis.conf 中设置

# 内存淘汰策略
maxmemory-policy volatile-lru

# 内存上限
maxmemory 4gb

# Hash优化
hash-max-ziplist-entries 512
hash-max-ziplist-value 64

# List优化
list-max-ziplist-size -2

# Set优化
set-max-intset-entries 512''',
            'slowlog_analysis': '''import redis

r = redis.Redis()
slowlogs = r.slowlog_get(100)

for log in slowlogs:
    print(f"ID: {log['id']}, 时间: {log['start_time']}")
    print(f"耗时: {log['duration']/1000:.2f}ms")
    print(f"命令: {' '.join(log['command'])}")
    print('-' * 50)''',
            'hot_key_cache': '''import redis
import cachetools

class HotKeyCache:
    def __init__(self, redis_client, maxsize=1000, ttl=60):
        self.redis = redis_client
        self.local_cache = cachetools.TTLCache(maxsize=maxsize, ttl=ttl)

    def get(self, key):
        if key in self.local_cache:
            return self.local_cache[key]
        value = self.redis.get(key)
        self.local_cache[key] = value
        return value'''
        }

        if optimization_type == 'all':
            return scripts
        return scripts.get(optimization_type, {})

