<template>
  <div class="list" @dragover.prevent @drop="handleDrop">
    <div class="list-header">
      <input
        v-if="isEditingTitle"
        v-model="editTitle"
        @blur="saveTitle"
        @keyup.enter="saveTitle"
        @keyup.esc="cancelEditingTitle"
        ref="titleInput"
        class="title-input"
      />
      <h3 v-else @click="startEditingTitle" class="list-title">{{ list.title }}</h3>
      <button class="delete-list-btn" @click="handleDeleteList" title="删除列表">&times;</button>
    </div>
    
    <div class="cards-container">
      <Card
        v-for="card in list.cards"
        :key="card.id"
        :card="card"
        :list-id="list.id"
      />
    </div>
    
    <div class="add-card-area">
      <div v-if="addingCard" class="add-card-form">
        <textarea
          v-model="newCardTitle"
          @keyup.enter="handleAddCard"
          @keyup.esc="cancelAddingCard"
          ref="cardInput"
          placeholder="输入卡片标题..."
          rows="3"
        ></textarea>
        <div class="add-card-actions">
          <button class="add-card-btn" @click="handleAddCard">添加卡片</button>
          <button class="cancel-btn" @click="cancelAddingCard">&times;</button>
        </div>
      </div>
      <button v-else class="add-card-trigger" @click="startAddingCard">
        + 添加卡片
      </button>
    </div>
  </div>
</template>

<script>
import Card from './Card.vue'

export default {
  name: 'List',
  components: {
    Card
  },
  props: {
    list: {
      type: Object,
      required: true
    }
  },
  data() {
    return {
      isEditingTitle: false,
      editTitle: '',
      addingCard: false,
      newCardTitle: ''
    }
  },
  methods: {
    startEditingTitle() {
      this.editTitle = this.list.title
      this.isEditingTitle = true
      this.$nextTick(() => {
        this.$refs.titleInput.focus()
        this.$refs.titleInput.select()
      })
    },
    saveTitle() {
      if (this.editTitle.trim() && this.editTitle.trim() !== this.list.title) {
        this.$store.dispatch('updateList', {
          id: this.list.id,
          updates: { title: this.editTitle.trim() }
        })
      }
      this.isEditingTitle = false
    },
    cancelEditingTitle() {
      this.isEditingTitle = false
    },
    handleDeleteList() {
      if (confirm('确定要删除这个列表及其所有卡片吗？')) {
        this.$store.dispatch('deleteList', this.list.id)
      }
    },
    startAddingCard() {
      this.addingCard = true
      this.$nextTick(() => {
        this.$refs.cardInput.focus()
      })
    },
    handleAddCard() {
      if (this.newCardTitle.trim()) {
        this.$store.dispatch('addCard', {
          listId: this.list.id,
          title: this.newCardTitle.trim()
        })
        this.newCardTitle = ''
      }
      this.addingCard = false
    },
    cancelAddingCard() {
      this.newCardTitle = ''
      this.addingCard = false
    },
    handleDrop(e) {
      const cardId = e.dataTransfer.getData('cardId')
      const fromListId = e.dataTransfer.getData('listId')
      
      if (cardId && fromListId && fromListId !== this.list.id) {
        this.$emit('move-card', {
          cardId,
          fromListId,
          toListId: this.list.id
        })
      }
    }
  }
}
</script>

<style scoped>
.list {
  background-color: #ebecf0;
  border-radius: 4px;
  width: 280px;
  min-width: 280px;
  max-height: 100%;
  display: flex;
  flex-direction: column;
  margin-right: 12px;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 8px 0;
}

.list-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #172b4d;
  cursor: pointer;
  padding: 4px 6px;
  border-radius: 4px;
  flex: 1;
}

.list-title:hover {
  background-color: rgba(9, 30, 66, 0.08);
}

.title-input {
  font-size: 14px;
  font-weight: 600;
  color: #172b4d;
  padding: 4px 6px;
  border: 2px solid #0079bf;
  border-radius: 4px;
  outline: none;
  flex: 1;
  font-family: inherit;
}

.delete-list-btn {
  background: none;
  border: none;
  color: #6b778c;
  font-size: 20px;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
}

.delete-list-btn:hover {
  background-color: rgba(9, 30, 66, 0.08);
  color: #b04632;
}

.cards-container {
  flex: 1;
  overflow-y: auto;
  padding: 0 8px;
  margin-top: 8px;
  min-height: 10px;
}

.add-card-area {
  padding: 8px;
}

.add-card-trigger {
  width: 100%;
  text-align: left;
  background: none;
  border: none;
  color: #5e6c84;
  padding: 8px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.2s;
}

.add-card-trigger:hover {
  background-color: rgba(9, 30, 66, 0.08);
  color: #172b4d;
}

.add-card-form textarea {
  width: 100%;
  border: none;
  border-radius: 4px;
  padding: 8px;
  font-size: 14px;
  resize: none;
  margin-bottom: 8px;
  font-family: inherit;
  box-shadow: inset 0 0 0 2px transparent;
}

.add-card-form textarea:focus {
  outline: none;
  box-shadow: inset 0 0 0 2px #0079bf;
}

.add-card-actions {
  display: flex;
  align-items: center;
}

.add-card-btn {
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

.add-card-btn:hover {
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
