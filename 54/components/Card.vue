<template>
  <div class="card" draggable="true" @dragstart="handleDragStart" @click.stop="openCardDetail">
    <div class="card-content">
      <p v-if="!isEditing">{{ card.title }}</p>
      <input
        v-else
        v-model="editTitle"
        @blur="saveTitle"
        @keyup.enter="saveTitle"
        @keyup.esc="cancelEditing"
        ref="editInput"
        @click.stop
      />
    </div>

    <div class="card-meta" v-if="hasAttachments || hasComments">
      <span v-if="hasAttachments" class="meta-item">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path>
        </svg>
        {{ card.attachments?.length || 0 }}
      </span>
      <span v-if="hasComments" class="meta-item">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
        </svg>
        {{ card.comments?.length || 0 }}
      </span>
    </div>

    <button class="delete-btn" @click.stop="handleDelete">&times;</button>

    <div v-if="showDetail" class="card-detail-modal" @click.stop>
      <div class="card-detail">
        <div class="detail-header">
          <h2 v-if="!isEditingDetailTitle" @dblclick="startEditDetailTitle" class="detail-title">
            {{ card.title }}
          </h2>
          <input
            v-else
            v-model="editDetailTitle"
            @blur="saveDetailTitle"
            @keyup.enter="saveDetailTitle"
            @keyup.esc="cancelEditDetailTitle"
            ref="detailTitleInput"
            class="detail-title-input"
          />
          <button class="close-btn" @click="closeCardDetail">&times;</button>
        </div>

        <div class="detail-section">
          <h4 class="section-title">附件</h4>
          <div class="attachments-list" v-if="card.attachments?.length">
            <div v-for="att in card.attachments" :key="att.id" class="attachment-item">
              <div v-if="att.isImage" class="attachment-thumbnail">
                <img :src="att.url" :alt="att.name" />
              </div>
              <div v-else class="attachment-icon">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                  <polyline points="14 2 14 8 20 8"></polyline>
                </svg>
              </div>
              <div class="attachment-info">
                <a :href="att.url" target="_blank" class="attachment-name">{{ att.name }}</a>
                <span class="attachment-size">{{ att.sizeFormatted }}</span>
              </div>
              <button class="attachment-delete" @click="removeAttachment(att)" title="删除附件">&times;</button>
            </div>
          </div>

          <div class="upload-area">
            <label class="upload-btn">
              <input
                type="file"
                ref="fileInput"
                @change="handleFileSelect"
                style="display: none"
                multiple
              />
              <span v-if="uploading">上传中... {{ uploadProgress }}%</span>
              <span v-else>+ 添加附件</span>
            </label>
            <div v-if="uploadError" class="error-msg">{{ uploadError }}</div>
          </div>
        </div>

        <div class="detail-section">
          <h4 class="section-title">评论</h4>
          <div class="comments-list">
            <div v-for="comment in card.comments" :key="comment.id" class="comment-item">
              <div class="comment-header">
                <span class="comment-author">{{ comment.userName }}</span>
                <span class="comment-time">{{ formatCommentTime(comment.createdAt) }}</span>
                <button class="comment-delete" @click="removeComment(comment)" title="删除评论">&times;</button>
              </div>
              <div class="comment-content" v-html="highlightMention(comment.content)"></div>
            </div>
          </div>

          <div class="add-comment">
            <textarea
              v-model="newComment"
              placeholder="添加评论，使用 @ 提醒他人..."
              @keyup.ctrl.enter="submitComment"
              rows="2"
            ></textarea>
            <div class="comment-actions">
              <button class="submit-comment-btn" @click="submitComment">
                发送评论
              </button>
              <span class="comment-tip">Ctrl+Enter 发送</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { highlightMentions } from '../activity_log'

export default {
  name: 'Card',
  props: {
    card: {
      type: Object,
      required: true
    },
    listId: {
      type: String,
      required: true
    }
  },
  data() {
    return {
      isEditing: false,
      editTitle: '',
      showDetail: false,
      isEditingDetailTitle: false,
      editDetailTitle: '',
      newComment: '',
      uploading: false,
      uploadProgress: 0,
      uploadError: ''
    }
  },
  computed: {
    hasAttachments() {
      return this.card.attachments && this.card.attachments.length > 0
    },
    hasComments() {
      return this.card.comments && this.card.comments.length > 0
    }
  },
  methods: {
    startEditing() {
      this.editTitle = this.card.title
      this.isEditing = true
      this.$nextTick(() => {
        this.$refs.editInput?.focus()
        this.$refs.editInput?.select()
      })
    },
    saveTitle() {
      if (this.editTitle.trim() && this.editTitle.trim() !== this.card.title) {
        this.$store.dispatch('updateCard', {
          listId: this.listId,
          cardId: this.card.id,
          updates: { title: this.editTitle.trim() }
        })
      }
      this.isEditing = false
    },
    cancelEditing() {
      this.isEditing = false
    },
    handleDelete(e) {
      e.stopPropagation()
      if (confirm('确定要删除这张卡片吗？')) {
        this.$store.dispatch('deleteCard', {
          listId: this.listId,
          cardId: this.card.id
        })
      }
    },
    handleDragStart(e) {
      e.dataTransfer.setData('cardId', this.card.id)
      e.dataTransfer.setData('listId', this.listId)
    },
    openCardDetail() {
      if (this.isEditing) return
      this.showDetail = true
      this.newComment = ''
    },
    closeCardDetail() {
      this.showDetail = false
      this.uploadError = ''
    },
    startEditDetailTitle() {
      this.editDetailTitle = this.card.title
      this.isEditingDetailTitle = true
      this.$nextTick(() => {
        this.$refs.detailTitleInput?.focus()
        this.$refs.detailTitleInput?.select()
      })
    },
    saveDetailTitle() {
      if (this.editDetailTitle.trim() && this.editDetailTitle.trim() !== this.card.title) {
        this.$store.dispatch('updateCard', {
          listId: this.listId,
          cardId: this.card.id,
          updates: { title: this.editDetailTitle.trim() }
        })
      }
      this.isEditingDetailTitle = false
    },
    cancelEditDetailTitle() {
      this.isEditingDetailTitle = false
    },
    handleFileSelect(e) {
      const files = Array.from(e.target.files)
      if (!files.length) return
      this.uploadFiles(files)
      e.target.value = ''
    },
    async uploadFiles(files) {
      this.uploading = true
      this.uploadError = ''

      for (const file of files) {
        try {
          await this.$store.dispatch('uploadCardAttachment', {
            listId: this.listId,
            cardId: this.card.id,
            file
          })
        } catch (error) {
          this.uploadError = error.message || '上传失败'
        }
      }

      this.uploading = false
    },
    removeAttachment(attachment) {
      if (confirm('确定要删除这个附件吗？')) {
        this.$store.dispatch('deleteCardAttachment', {
          listId: this.listId,
          cardId: this.card.id,
          attachment
        })
      }
    },
    submitComment() {
      const content = this.newComment.trim()
      if (!content) return

      this.$store.dispatch('addCardComment', {
        listId: this.listId,
        cardId: this.card.id,
        content
      })
      this.newComment = ''
    },
    removeComment(comment) {
      if (confirm('确定要删除这条评论吗？')) {
        this.$store.dispatch('deleteCardComment', {
          listId: this.listId,
          cardId: this.card.id,
          comment
        })
      }
    },
    formatCommentTime(timestamp) {
      if (!timestamp) return ''
      const date = timestamp instanceof Date ? timestamp : new Date(timestamp)
      const now = new Date()
      const diff = now - date
      const minutes = Math.floor(diff / 60000)
      const hours = Math.floor(diff / 3600000)
      const days = Math.floor(diff / 86400000)

      if (minutes < 1) return '刚刚'
      if (minutes < 60) return `${minutes}分钟前`
      if (hours < 24) return `${hours}小时前`
      if (days < 7) return `${days}天前`
      return date.toLocaleDateString('zh-CN')
    },
    highlightMention(text) {
      return highlightMentions(text)
    }
  }
}
</script>

<style scoped>
.card {
  background: #fff;
  border-radius: 4px;
  padding: 10px;
  margin-bottom: 8px;
  box-shadow: 0 1px 0 rgba(9, 30, 66, 0.25);
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  transition: background-color 0.2s;
  position: relative;
}

.card:hover {
  background-color: #f4f5f7;
}

.card-content {
  flex: 1;
}

.card-content p {
  margin: 0;
  color: #172b4d;
  font-size: 14px;
  line-height: 1.4;
  word-break: break-word;
}

.card-content input {
  width: 100%;
  border: none;
  font-size: 14px;
  padding: 0;
  outline: none;
  font-family: inherit;
}

.card-meta {
  display: flex;
  gap: 8px;
  margin-top: 6px;
  color: #5e6c84;
  font-size: 12px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 2px;
}

.delete-btn {
  background: none;
  border: none;
  color: #6b778c;
  font-size: 18px;
  cursor: pointer;
  padding: 0 4px;
  margin-left: 4px;
  opacity: 0;
  transition: opacity 0.2s;
}

.card:hover .delete-btn {
  opacity: 1;
}

.delete-btn:hover {
  color: #b04632;
}

.card-detail-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 40px 20px;
  z-index: 1000;
  overflow-y: auto;
}

.card-detail {
  background: #f4f5f7;
  border-radius: 4px;
  width: 100%;
  max-width: 768px;
  min-height: 200px;
  padding: 20px;
  position: relative;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}

.detail-title {
  margin: 0;
  color: #172b4d;
  font-size: 20px;
  font-weight: 600;
  flex: 1;
  margin-right: 20px;
  cursor: text;
  padding: 4px;
}

.detail-title:hover {
  background: rgba(9, 30, 66, 0.04);
}

.detail-title-input {
  flex: 1;
  font-size: 20px;
  font-weight: 600;
  padding: 4px;
  border: 2px solid #0079bf;
  border-radius: 4px;
  outline: none;
  margin-right: 20px;
  font-family: inherit;
}

.close-btn {
  background: none;
  border: none;
  font-size: 28px;
  color: #6b778c;
  cursor: pointer;
  line-height: 1;
  padding: 4px;
}

.close-btn:hover {
  color: #172b4d;
}

.detail-section {
  margin-bottom: 24px;
}

.section-title {
  margin: 0 0 12px;
  color: #172b4d;
  font-size: 14px;
  font-weight: 600;
}

.attachments-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.attachment-item {
  display: flex;
  align-items: center;
  background: #fff;
  border-radius: 4px;
  padding: 8px;
  gap: 12px;
  position: relative;
}

.attachment-thumbnail img {
  width: 64px;
  height: 64px;
  object-fit: cover;
  border-radius: 4px;
}

.attachment-icon {
  color: #6b778c;
}

.attachment-info {
  flex: 1;
}

.attachment-name {
  display: block;
  color: #0079bf;
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
}

.attachment-name:hover {
  text-decoration: underline;
}

.attachment-size {
  color: #5e6c84;
  font-size: 12px;
}

.attachment-delete {
  background: none;
  border: none;
  font-size: 18px;
  color: #6b778c;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.2s;
  padding: 0 4px;
}

.attachment-item:hover .attachment-delete {
  opacity: 1;
}

.attachment-delete:hover {
  color: #b04632;
}

.upload-btn {
  display: inline-block;
  background: #0079bf;
  color: #fff;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.2s;
}

.upload-btn:hover {
  background: #026aa7;
}

.error-msg {
  color: #b04632;
  font-size: 12px;
  margin-top: 8px;
}

.comments-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 16px;
}

.comment-item {
  background: #fff;
  border-radius: 4px;
  padding: 12px;
  position: relative;
}

.comment-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.comment-author {
  font-weight: 600;
  color: #172b4d;
  font-size: 14px;
}

.comment-time {
  color: #5e6c84;
  font-size: 12px;
}

.comment-delete {
  position: absolute;
  top: 8px;
  right: 8px;
  background: none;
  border: none;
  font-size: 16px;
  color: #6b778c;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.2s;
}

.comment-item:hover .comment-delete {
  opacity: 1;
}

.comment-delete:hover {
  color: #b04632;
}

.comment-content {
  color: #172b4d;
  font-size: 14px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

.comment-content :deep(.mention) {
  color: #0079bf;
  font-weight: 600;
}

.add-comment {
  background: #fff;
  border-radius: 4px;
  padding: 12px;
}

.add-comment textarea {
  width: 100%;
  border: 1px solid #dfe1e6;
  border-radius: 4px;
  padding: 8px;
  font-size: 14px;
  resize: vertical;
  font-family: inherit;
  box-sizing: border-box;
}

.add-comment textarea:focus {
  outline: none;
  border-color: #0079bf;
}

.comment-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 8px;
}

.submit-comment-btn {
  background: #0079bf;
  color: #fff;
  border: none;
  border-radius: 4px;
  padding: 8px 16px;
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.submit-comment-btn:hover {
  background: #026aa7;
}

.comment-tip {
  color: #5e6c84;
  font-size: 12px;
}
</style>
