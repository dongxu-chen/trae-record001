package hashslot

import (
	"hash/crc16"
)

const DefaultSlotCount = 16384

type HashSlot struct {
	slotCount int
}

func New(slotCount int) *HashSlot {
	if slotCount <= 0 {
		slotCount = DefaultSlotCount
	}
	return &HashSlot{slotCount: slotCount}
}

func (h *HashSlot) GetSlot(key string) int {
	if key == "" {
		return 0
	}
	hash := crc16.Checksum([]byte(key), crc16.IBMTable)
	return int(hash) % h.slotCount
}

func (h *HashSlot) GetSlotForKey(key string) int {
	if start := indexOf(key, '{'); start != -1 {
		if end := indexOf(key[start+1:], '}'); end != -1 && end > 0 {
			hashKey := key[start+1 : start+1+end]
			if hashKey != "" {
				return h.GetSlot(hashKey)
			}
		}
	}
	return h.GetSlot(key)
}

func (h *HashSlot) GetShardIndex(key string, shardTotal int) int {
	if shardTotal <= 1 {
		return 0
	}
	slot := h.GetSlotForKey(key)
	slotsPerShard := h.slotCount / shardTotal
	if slotsPerShard == 0 {
		slotsPerShard = 1
	}
	return slot / slotsPerShard
}

func (h *HashSlot) GetSlotRange(shardIndex, shardTotal int) (start, end int) {
	if shardTotal <= 1 {
		return 0, h.slotCount - 1
	}
	slotsPerShard := h.slotCount / shardTotal
	remainder := h.slotCount % shardTotal

	start = shardIndex * slotsPerShard
	if shardIndex < remainder {
		start += shardIndex
		end = start + slotsPerShard
	} else {
		start += remainder
		end = start + slotsPerShard - 1
	}

	if end >= h.slotCount {
		end = h.slotCount - 1
	}
	return start, end
}

func (h *HashSlot) SlotCount() int {
	return h.slotCount
}

func indexOf(s string, b byte) int {
	for i := 0; i < len(s); i++ {
		if s[i] == b {
			return i
		}
	}
	return -1
}
