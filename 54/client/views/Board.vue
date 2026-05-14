<template>
  <div class="board-wrapper">
    <header class="board-header">
      <h1 class="board-title">任务管理面板</h1>
    </header>
    
    <main class="board-content">
      <div v-if="loading" class="loading">
        加载中...
      </div>
      
      <div v-else class="lists-container">
        <List
          v-for="list in lists"
          :key="list.id"
          :list="list"
          @move-card="handleMoveCard"
        />
        
        <div class="add-list-area">
          <div v-if="addingList" class="add-list-form">
            <input
              v-model="newListTitle"
              @keyup.enter="handleAddList"
              @keyup.esc="cancelAddingList"
              ref="listInput"
              placeholder="输入列表标题..."
            />
            <div class="add-list-actions">
              <button class="add-list-btn" @click="handleAddList">添加列表</button>
              <button class="cancel-btn" @click="cancelAddingList">&times;</button>
            </div>
          </div>
          <button v-else class="add-list-trigger" @click="startAddingList">
            + 添加列表
          </button>
        </div>
      </div>
    </main>
  </div>
</template>

<script>
import { mapState } from 'vuex'
import List from '../../components/List.vue'

export default {
  name: 'Board',
  components: {
    List
  },
  computed: {
    ...mapState(['lists', 'loading'])
  },
  data() {
    return {
      addingList: false,
      newListTitle: ''
    }
  },
  mounted() {
    this.$store.dispatch('subscribeLists')
  },
  beforeUnmount() {
    this.$store.dispatch('unsubscribeLists')
  },
  methods: {
    startAddingList() {
      this.addingList = true
      this.$nextTick(() => {
        this.$refs.listInput.focus()
      })
    },
    handleAddList() {
      if (this.newListTitle.trim()) {
        this.$store.dispatch('addList', {
          title: this.newListTitle.trim()
        })
        this.newListTitle = ''
      }
      this.addingList = false
    },
    cancelAddingList() {
      this.newListTitle = ''
      this.addingList = false
    },
    async handleMoveCard({ cardId, fromListId, toListId }) {
      if (fromListId === toListId) return
      
      const fromList = this.lists.find(l => l.id === fromListId)
      const card = fromList?.cards?.find(c => c.id === cardId)
      
      if (!card) return
      
      const toList = this.lists.find(l => l.id === toListId)
      const newOrder = toList && toList.cards ? toList.cards.length : 0
      
      try {
        await this.$store.dispatch('moveCard', {
          cardId,
          fromListId,
          toListId,
          card,
          newOrder
        })
      } catch (error) {
        console.error('移动卡片失败:', error)
      }
    }
  }
}
</script>

<style scoped>
.board-wrapper {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: linear-gradient(135deg, #0079bf, #5067c5);
}

.board-header {
  background: rgba(0, 0, 0, 0.15);
  padding: 12px 20px;
  backdrop-filter: blur(4px);
}

.board-title {
  margin: 0;
  color: #fff;
  font-size: 20px;
  font-weight: 600;
}

.board-content {
  flex: 1;
  padding: 20px;
  overflow-x: auto;
}

.loading {
  color: #fff;
  text-align: center;
  padding: 40px;
  font-size: 16px;
}

.lists-container {
  display: flex;
  align-items: flex-start;
  height: 100%;
}

.add-list-area {
  min-width: 280px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  transition: background-color 0.2s;
}

.add-list-area:hover {
  background: rgba(255, 255, 255, 0.2);
}

.add-list-trigger {
  width: 100%;
  text-align: left;
  background: none;
  border: none;
  color: #fff;
  padding: 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
}

.add-list-form {
  padding: 8px;
  background: #ebecf0;
  border-radius: 4px;
}

.add-list-form input {
  width: 100%;
  border: none;
  border-radius: 4px;
  padding: 8px 12px;
  font-size: 14px;
  margin-bottom: 8px;
  font-family: inherit;
  box-shadow: inset 0 0 0 2px transparent;
}

.add-list-form input:focus {
  outline: none;
  box-shadow: inset 0 0 0 2px #0079bf;
}

.add-list-actions {
  display: flex;
  align-items: center;
}

.add-list-btn {
  background-color: #0079bf;
  color: #fff;
  border: none;
  border-radius: 4px;
  padding: 8px 16px;
  font-size: 14px;
  cursor: pointer;
  margin-right: 8px;
  transition: background-color 0.2s;
}

.add-list-btn:hover {
  background-color: #026aa7;
}

.cancel-btn {
  background: none;
  border: none;
  font-size: 24px;
  color: #6b778c;
  cursor: pointer;
  padding: 0 4px;
}

.cancel-btn:hover {
  color: #172b4d;
}
</style>
