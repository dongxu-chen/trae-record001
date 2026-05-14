<template>
  <div class="notification-container">
    <button class="bell-btn" @click="togglePanel" :class="{ has-unread: unreadCount > 0 }">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
        <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
      </svg>
      <span v-if="unreadCount > 0" class="badge">{{ unreadCount > 99 ? '99+' : unreadCount }}</span>
    </button>

    <transition name="slide-down">
      <div v-if="showPanel" class="notification-panel" @click.stop>
        <div class="panel-header">
          <h3 class="panel-title">通知</h3>
          <button
            v-if="unreadCount > 0"
            class="mark-all-read-btn"
            @click="markAllRead"
          >
            全部已读
          </button>
        </div>

        <div class="panel-body">
          <div v-if="loading" class="loading-state">
            加载中...
          </div>

          <div v-else-if="notifications.length === 0" class="empty-state">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#97a4af" stroke-width="1.5">
              <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
              <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
            </svg>
            <p>暂无通知</p>
          </div>

          <div v-else class="notifications-list">
            <div
              v-for="notification in notifications"
              :key="notification.id"
              class="notification-item"
              :class="{ unread: !notification.read }"
              @click="handleNotificationClick(notification)"
            >
              <div class="notification-icon">
                <component :is="getNotificationIcon(notification.type)" />
              </div>

              <div class="notification-content">
                <p class="notification-text">{{ notification.description }}</p>
                <span class="notification-time">{{ notification.timeAgo }}</span>
              </div>

              <div v-if="!notification.read" class="unread-dot"></div>
            </div>
          </div>
        </div>
      </div>
    </transition>

    <div v-if="showPanel" class="overlay" @click="showPanel = false"></div>
  </div>
</template>

<script>
import { computed, reactive, h } from 'vue'
import { useStore } from 'vuex'

export default {
  name: 'Notification',
  setup() {
    const store = useStore()
    const state = reactive({
      showPanel: false,
      loading: false
    })

    const notifications = computed(() => store.state.notifications)
    const unreadCount = computed(() => store.getters.unreadNotificationCount || store.state.notificationsUnread)

    const togglePanel = () => {
      state.showPanel = !state.showPanel
    }

    const markAllRead = () => {
      store.dispatch('markAllNotificationsRead')
    }

    const handleNotificationClick = (notification) => {
      if (!notification.read) {
        store.dispatch('markNotificationRead', notification.id)
      }
    }

    const getNotificationIcon = (type) => {
      const iconComponents = {
        mentioned: () => h('svg', {
          width: 20,
          height: 20,
          viewBox: '0 0 24 24',
          fill: 'none',
          stroke: 'currentColor',
          'stroke-width': '2'
        }, [
          h('circle', { cx: 12, cy: 12, r: 4 }),
          h('path', { d: 'M16 8v5a3 3 0 0 0 6 0v-1a10 10 0 1 0-3.92 7.94' })
        ]),
        comment_added: () => h('svg', {
          width: 20,
          height: 20,
          viewBox: '0 0 24 24',
          fill: 'none',
          stroke: 'currentColor',
          'stroke-width': '2'
        }, [
          h('path', { d: 'M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z' })
        ]),
        attachment_uploaded: () => h('svg', {
          width: 20,
          height: 20,
          viewBox: '0 0 24 24',
          fill: 'none',
          stroke: 'currentColor',
          'stroke-width': '2'
        }, [
          h('path', { d: 'M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48' })
        ]),
        card_moved: () => h('svg', {
          width: 20,
          height: 20,
          viewBox: '0 0 24 24',
          fill: 'none',
          stroke: 'currentColor',
          'stroke-width': '2'
        }, [
          h('path', { d: 'M5 9l6-6 6 6' }),
          h('path', { d: 'M5 15l6 6 6-6' })
        ]),
        default: () => h('svg', {
          width: 20,
          height: 20,
          viewBox: '0 0 24 24',
          fill: 'none',
          stroke: 'currentColor',
          'stroke-width': '2'
        }, [
          h('circle', { cx: 12, cy: 12, r: 10 }),
          h('line', { x1: 12, y1: 8, x2: 12, y2: 12 }),
          h('line', { x1: 12, y1: 16, x2: 12.01, y2: 16 })
        ])
      }
      return iconComponents[type] || iconComponents.default
    }

    return {
      notifications,
      unreadCount,
      showPanel: computed(() => state.showPanel),
      loading: computed(() => state.loading),
      togglePanel,
      markAllRead,
      handleNotificationClick,
      getNotificationIcon
    }
  },
  mounted() {
    this.$store.dispatch('subscribeNotifications')
  },
  beforeUnmount() {
    this.$store.dispatch('unsubscribeNotifications')
  }
}
</script>

<style scoped>
.notification-container {
  position: relative;
}

.bell-btn {
  background: none;
  border: none;
  color: #fff;
  cursor: pointer;
  padding: 8px;
  border-radius: 4px;
  position: relative;
  transition: background-color 0.2s;
}

.bell-btn:hover {
  background: rgba(255, 255, 255, 0.15);
}

.bell-btn.has-unread {
  color: #fff;
}

.badge {
  position: absolute;
  top: 2px;
  right: 2px;
  background: #cf1322;
  color: #fff;
  font-size: 10px;
  font-weight: 600;
  padding: 2px 5px;
  border-radius: 10px;
  min-width: 16px;
  text-align: center;
  line-height: 1.2;
}

.overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 998;
}

.notification-panel {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 8px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
  width: 360px;
  max-height: 480px;
  display: flex;
  flex-direction: column;
  z-index: 999;
  overflow: hidden;
}

.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 0.2s ease;
}

.slide-down-enter-from,
.slide-down-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #e8e8e8;
}

.panel-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #172b4d;
}

.mark-all-read-btn {
  background: none;
  border: none;
  color: #0079bf;
  font-size: 13px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.mark-all-read-btn:hover {
  background: #f4f5f7;
}

.panel-body {
  flex: 1;
  overflow-y: auto;
  max-height: 400px;
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: #5e6c84;
  font-size: 14px;
}

.empty-state svg {
  margin-bottom: 12px;
}

.empty-state p {
  margin: 0;
}

.notifications-list {
  display: flex;
  flex-direction: column;
}

.notification-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 16px;
  cursor: pointer;
  transition: background-color 0.2s;
  position: relative;
}

.notification-item:hover {
  background: #f4f5f7;
}

.notification-item.unread {
  background: #e9f2ff;
}

.notification-item.unread:hover {
  background: #dbeafe;
}

.notification-icon {
  color: #0079bf;
  flex-shrink: 0;
  margin-top: 2px;
}

.notification-item.unread .notification-icon {
  color: #1890ff;
}

.notification-content {
  flex: 1;
  min-width: 0;
}

.notification-text {
  margin: 0;
  color: #172b4d;
  font-size: 14px;
  line-height: 1.4;
  word-break: break-word;
}

.notification-time {
  display: block;
  color: #5e6c84;
  font-size: 12px;
  margin-top: 4px;
}

.unread-dot {
  width: 8px;
  height: 8px;
  background: #1890ff;
  border-radius: 50%;
  flex-shrink: 0;
  margin-top: 6px;
}
</style>
