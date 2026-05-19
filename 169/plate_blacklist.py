import json
import os
import uuid
from datetime import datetime
from collections import defaultdict
import threading


class PlateListManager:
    def __init__(self, data_file='plate_lists.json'):
        self.data_file = data_file
        self.whitelist = {}
        self.blacklist = {}
        self.alert_history = []
        self.callbacks = {
            'on_whitelist_match': None,
            'on_blacklist_match': None,
            'on_alert': None
        }
        self._lock = threading.Lock()
        self._load_data()

    def _load_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.whitelist = data.get('whitelist', {})
                    self.blacklist = data.get('blacklist', {})
                    self.alert_history = data.get('alert_history', [])
            except Exception as e:
                print(f"Error loading plate lists: {e}")
                self.whitelist = {}
                self.blacklist = {}
                self.alert_history = []

    def _save_data(self):
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'whitelist': self.whitelist,
                    'blacklist': self.blacklist,
                    'alert_history': self.alert_history[-1000:]
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving plate lists: {e}")

    def set_callback(self, event_name, callback):
        if event_name in self.callbacks:
            self.callbacks[event_name] = callback

    def add_to_whitelist(self, plate_number, owner=None, vehicle_type=None, description=None, valid_from=None, valid_to=None):
        with self._lock:
            plate_number = plate_number.upper().strip()
            if plate_number in self.whitelist:
                return {'success': False, 'message': '车牌已在白名单中'}
            
            entry = {
                'id': str(uuid.uuid4()),
                'plate_number': plate_number,
                'owner': owner,
                'vehicle_type': vehicle_type,
                'description': description,
                'valid_from': valid_from or datetime.now().isoformat(),
                'valid_to': valid_to,
                'created_at': datetime.now().isoformat(),
                'is_active': True
            }
            self.whitelist[plate_number] = entry
            self._save_data()
            return {'success': True, 'message': '添加成功', 'data': entry}

    def add_to_blacklist(self, plate_number, reason=None, level='medium', description=None, valid_from=None, valid_to=None):
        with self._lock:
            plate_number = plate_number.upper().strip()
            if plate_number in self.blacklist:
                return {'success': False, 'message': '车牌已在黑名单中'}
            
            entry = {
                'id': str(uuid.uuid4()),
                'plate_number': plate_number,
                'reason': reason,
                'level': level,
                'description': description,
                'valid_from': valid_from or datetime.now().isoformat(),
                'valid_to': valid_to,
                'created_at': datetime.now().isoformat(),
                'is_active': True
            }
            self.blacklist[plate_number] = entry
            self._save_data()
            return {'success': True, 'message': '添加成功', 'data': entry}

    def remove_from_whitelist(self, plate_number):
        with self._lock:
            plate_number = plate_number.upper().strip()
            if plate_number in self.whitelist:
                del self.whitelist[plate_number]
                self._save_data()
                return {'success': True, 'message': '移除成功'}
            return {'success': False, 'message': '车牌不在白名单中'}

    def remove_from_blacklist(self, plate_number):
        with self._lock:
            plate_number = plate_number.upper().strip()
            if plate_number in self.blacklist:
                del self.blacklist[plate_number]
                self._save_data()
                return {'success': True, 'message': '移除成功'}
            return {'success': False, 'message': '车牌不在黑名单中'}

    def check_plate(self, plate_number):
        if not plate_number:
            return {
                'is_whitelist': False,
                'is_blacklist': False,
                'whitelist_info': None,
                'blacklist_info': None,
                'match_type': 'unknown'
            }
        
        plate_number = plate_number.upper().strip()
        result = {
            'is_whitelist': False,
            'is_blacklist': False,
            'whitelist_info': None,
            'blacklist_info': None,
            'match_type': 'none'
        }
        
        with self._lock:
            if plate_number in self.whitelist:
                info = self.whitelist[plate_number]
                if self._is_valid_entry(info):
                    result['is_whitelist'] = True
                    result['whitelist_info'] = info
                    result['match_type'] = 'whitelist'
            
            if plate_number in self.blacklist:
                info = self.blacklist[plate_number]
                if self._is_valid_entry(info):
                    result['is_blacklist'] = True
                    result['blacklist_info'] = info
                    if result['match_type'] == 'whitelist':
                        result['match_type'] = 'conflict'
                    else:
                        result['match_type'] = 'blacklist'
        
        return result

    def _is_valid_entry(self, entry):
        if not entry.get('is_active', True):
            return False
        
        now = datetime.now()
        
        if entry.get('valid_from'):
            try:
                valid_from = datetime.fromisoformat(entry['valid_from'])
                if now < valid_from:
                    return False
            except:
                pass
        
        if entry.get('valid_to'):
            try:
                valid_to = datetime.fromisoformat(entry['valid_to'])
                if now > valid_to:
                    return False
            except:
                pass
        
        return True

    def check_and_alert(self, plate_number, extra_info=None):
        check_result = self.check_plate(plate_number)
        
        if check_result['match_type'] == 'whitelist':
            if self.callbacks['on_whitelist_match']:
                try:
                    self.callbacks['on_whitelist_match'](check_result, extra_info)
                except Exception as e:
                    print(f"Whitelist callback error: {e}")
        
        elif check_result['match_type'] == 'blacklist':
            alert = self._create_alert(check_result, extra_info)
            
            if self.callbacks['on_blacklist_match']:
                try:
                    self.callbacks['on_blacklist_match'](check_result, alert, extra_info)
                except Exception as e:
                    print(f"Blacklist callback error: {e}")
            
            if self.callbacks['on_alert']:
                try:
                    self.callbacks['on_alert'](alert)
                except Exception as e:
                    print(f"Alert callback error: {e}")
        
        return check_result

    def _create_alert(self, check_result, extra_info=None):
        blacklist_info = check_result['blacklist_info']
        alert = {
            'id': str(uuid.uuid4()),
            'plate_number': check_result['blacklist_info']['plate_number'],
            'alert_type': 'blacklist',
            'level': blacklist_info.get('level', 'medium'),
            'reason': blacklist_info.get('reason', ''),
            'description': blacklist_info.get('description', ''),
            'timestamp': datetime.now().isoformat(),
            'extra_info': extra_info or {},
            'acknowledged': False,
            'acknowledged_at': None,
            'acknowledged_by': None
        }
        
        with self._lock:
            self.alert_history.append(alert)
            if len(self.alert_history) > 1000:
                self.alert_history = self.alert_history[-1000:]
            self._save_data()
        
        return alert

    def get_whitelist(self, page=1, page_size=50):
        with self._lock:
            items = list(self.whitelist.values())
            total = len(items)
            start = (page - 1) * page_size
            end = start + page_size
            return {
                'items': items[start:end],
                'total': total,
                'page': page,
                'page_size': page_size
            }

    def get_blacklist(self, page=1, page_size=50):
        with self._lock:
            items = list(self.blacklist.values())
            total = len(items)
            start = (page - 1) * page_size
            end = start + page_size
            return {
                'items': items[start:end],
                'total': total,
                'page': page,
                'page_size': page_size
            }

    def get_alert_history(self, page=1, page_size=50, acknowledged=None, level=None):
        with self._lock:
            items = list(self.alert_history)
            items.reverse()
            
            if acknowledged is not None:
                items = [a for a in items if a.get('acknowledged') == acknowledged]
            
            if level:
                items = [a for a in items if a.get('level') == level]
            
            total = len(items)
            start = (page - 1) * page_size
            end = start + page_size
            return {
                'items': items[start:end],
                'total': total,
                'page': page,
                'page_size': page_size
            }

    def acknowledge_alert(self, alert_id, acknowledged_by=None):
        with self._lock:
            for alert in self.alert_history:
                if alert['id'] == alert_id:
                    alert['acknowledged'] = True
                    alert['acknowledged_at'] = datetime.now().isoformat()
                    alert['acknowledged_by'] = acknowledged_by
                    self._save_data()
                    return {'success': True, 'message': '告警已确认', 'data': alert}
            return {'success': False, 'message': '告警不存在'}

    def get_statistics(self):
        with self._lock:
            active_whitelist = sum(1 for e in self.whitelist.values() if self._is_valid_entry(e))
            active_blacklist = sum(1 for e in self.blacklist.values() if self._is_valid_entry(e))
            unacknowledged = sum(1 for a in self.alert_history if not a.get('acknowledged'))
            
            level_counts = defaultdict(int)
            for alert in self.alert_history:
                if not alert.get('acknowledged'):
                    level_counts[alert.get('level', 'unknown')] += 1
            
            return {
                'whitelist_total': len(self.whitelist),
                'whitelist_active': active_whitelist,
                'blacklist_total': len(self.blacklist),
                'blacklist_active': active_blacklist,
                'alerts_total': len(self.alert_history),
                'alerts_unacknowledged': unacknowledged,
                'alerts_by_level': dict(level_counts)
            }

    def batch_import(self, whitelist_items=None, blacklist_items=None):
        results = {'whitelist': {'success': 0, 'failed': 0, 'errors': []},
                  'blacklist': {'success': 0, 'failed': 0, 'errors': []}}
        
        if whitelist_items:
            for item in whitelist_items:
                try:
                    result = self.add_to_whitelist(
                        item.get('plate_number'),
                        item.get('owner'),
                        item.get('vehicle_type'),
                        item.get('description'),
                        item.get('valid_from'),
                        item.get('valid_to')
                    )
                    if result['success']:
                        results['whitelist']['success'] += 1
                    else:
                        results['whitelist']['failed'] += 1
                        results['whitelist']['errors'].append({'item': item, 'error': result['message']})
                except Exception as e:
                    results['whitelist']['failed'] += 1
                    results['whitelist']['errors'].append({'item': item, 'error': str(e)})
        
        if blacklist_items:
            for item in blacklist_items:
                try:
                    result = self.add_to_blacklist(
                        item.get('plate_number'),
                        item.get('reason'),
                        item.get('level', 'medium'),
                        item.get('description'),
                        item.get('valid_from'),
                        item.get('valid_to')
                    )
                    if result['success']:
                        results['blacklist']['success'] += 1
                    else:
                        results['blacklist']['failed'] += 1
                        results['blacklist']['errors'].append({'item': item, 'error': result['message']})
                except Exception as e:
                    results['blacklist']['failed'] += 1
                    results['blacklist']['errors'].append({'item': item, 'error': str(e)})
        
        return results

    def clear_all(self):
        with self._lock:
            self.whitelist.clear()
            self.blacklist.clear()
            self.alert_history.clear()
            self._save_data()
            return {'success': True, 'message': '所有数据已清空'}
