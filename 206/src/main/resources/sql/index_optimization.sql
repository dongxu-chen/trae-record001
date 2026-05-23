USE meeting_booking;

ALTER TABLE booking DROP INDEX IF EXISTS idx_room_time;
ALTER TABLE booking DROP INDEX IF EXISTS idx_user_id;
ALTER TABLE booking DROP INDEX IF EXISTS idx_status;

ALTER TABLE booking ADD INDEX IF NOT EXISTS idx_room_status_time (room_id, status, start_time, end_time);
ALTER TABLE booking ADD INDEX IF NOT EXISTS idx_user_status_time (user_id, status, start_time);
ALTER TABLE booking ADD INDEX IF NOT EXISTS idx_status_time (status, start_time);
ALTER TABLE booking ADD INDEX IF NOT EXISTS idx_recurring (is_recurring, recurring_parent_id);
ALTER TABLE booking ADD INDEX IF NOT EXISTS idx_create_time (create_time);

ALTER TABLE meeting_room ADD INDEX IF NOT EXISTS idx_status_capacity (status, capacity);

ALTER TABLE equipment ADD INDEX IF NOT EXISTS idx_status_type (status, type);

EXPLAIN SELECT * FROM booking 
WHERE room_id = 1 AND status IN (1, 2) 
AND start_time < '2024-12-31 23:59:59' 
AND end_time > '2024-01-01 00:00:00';

EXPLAIN SELECT * FROM booking 
WHERE user_id = 1 AND status = 2 
ORDER BY start_time DESC 
LIMIT 10 OFFSET 0;
