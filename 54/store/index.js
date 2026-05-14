import { createStore } from 'vuex'
import {
  collection,
  addDoc,
  updateDoc,
  deleteDoc,
  doc,
  query,
  orderBy,
  onSnapshot,
  arrayUnion,
  arrayRemove,
  serverTimestamp
} from 'firebase/firestore'
import { db, addListener, removeListener, clearAllListeners, hasListener } from '../firebase'
import { uploadAttachment, deleteAttachment } from '../upload'
import { logActivity, ACTIVITY_TYPES, extractMentions, formatTimeAgo } from '../activity_log'

const LIST_LISTENER_KEY = 'board_lists'
const NOTIFICATION_LISTENER_KEY = 'notifications'

const CURRENT_USER = {
  id: 'user_001',
  name: '当前用户',
  userName: 'current_user'
}

export default createStore({
  state() {
    return {
      lists: [],
      loading: false,
      notifications: [],
      notificationsUnread: 0,
      selectedCard: null,
      selectedListId: null,
      uploadProgress: {}
    }
  },
  getters: {
    getCardsByListId: (state) => (listId) => {
      const list = state.lists.find(l => l.id === listId)
      return list ? list.cards || [] : []
    },
    unreadNotificationCount: (state) => {
      return state.notifications.filter(n => !n.read).length
    }
  },
  mutations: {
    SET_LISTS(state, lists) {
      state.lists = lists
    },
    ADD_LIST(state, list) {
      state.lists = [...state.lists, list]
    },
    UPDATE_LIST(state, { id, updates }) {
      state.lists = state.lists.map(list =>
        list.id === id ? { ...list, ...updates } : list
      )
    },
    DELETE_LIST(state, id) {
      state.lists = state.lists.filter(l => l.id !== id)
    },
    ADD_CARD(state, { listId, card }) {
      state.lists = state.lists.map(list => {
        if (list.id !== listId) return list
        const cards = list.cards ? [...list.cards, card] : [card]
        return { ...list, cards }
      })
    },
    UPDATE_CARD(state, { listId, cardId, updates }) {
      state.lists = state.lists.map(list => {
        if (list.id !== listId) return list
        const cards = list.cards.map(card =>
          card.id === cardId ? { ...card, ...updates } : card
        )
        return { ...list, cards }
      })
    },
    DELETE_CARD(state, { listId, cardId }) {
      state.lists = state.lists.map(list => {
        if (list.id !== listId) return list
        const cards = list.cards.filter(c => c.id !== cardId)
        return { ...list, cards }
      })
    },
    MOVE_CARD(state, { cardId, fromListId, toListId, card, newOrder }) {
      let movedCard = card

      state.lists = state.lists.map(list => {
        if (list.id === fromListId) {
          const fromCards = list.cards || []
          movedCard = movedCard || fromCards.find(c => c.id === cardId)
          const cards = fromCards.filter(c => c.id !== cardId)
          return { ...list, cards }
        }
        if (list.id === toListId) {
          const cards = list.cards ? [...list.cards] : []
          if (movedCard) {
            const cardToMove = { ...movedCard, order: newOrder }
            if (newOrder >= cards.length) {
              cards.push(cardToMove)
            } else {
              cards.splice(newOrder, 0, cardToMove)
            }
          }
          return { ...list, cards }
        }
        return list
      })
    },
    ADD_ATTACHMENT(state, { listId, cardId, attachment }) {
      state.lists = state.lists.map(list => {
        if (list.id !== listId) return list
        const cards = list.cards.map(card => {
          if (card.id !== cardId) return card
          const attachments = card.attachments ? [...card.attachments, attachment] : [attachment]
          return { ...card, attachments }
        })
        return { ...list, cards }
      })
    },
    DELETE_ATTACHMENT(state, { listId, cardId, attachmentId }) {
      state.lists = state.lists.map(list => {
        if (list.id !== listId) return list
        const cards = list.cards.map(card => {
          if (card.id !== cardId) return card
          const attachments = (card.attachments || []).filter(a => a.id !== attachmentId)
          return { ...card, attachments }
        })
        return { ...list, cards }
      })
    },
    ADD_COMMENT(state, { listId, cardId, comment }) {
      state.lists = state.lists.map(list => {
        if (list.id !== listId) return list
        const cards = list.cards.map(card => {
          if (card.id !== cardId) return card
          const comments = card.comments ? [...card.comments, comment] : [comment]
          return { ...card, comments }
        })
        return { ...list, cards }
      })
    },
    DELETE_COMMENT(state, { listId, cardId, commentId }) {
      state.lists = state.lists.map(list => {
        if (list.id !== listId) return list
        const cards = list.cards.map(card => {
          if (card.id !== cardId) return card
          const comments = (card.comments || []).filter(c => c.id !== commentId)
          return { ...card, comments }
        })
        return { ...list, cards }
      })
    },
    SET_LOADING(state, loading) {
      state.loading = loading
    },
    SET_NOTIFICATIONS(state, notifications) {
      state.notifications = notifications
      state.notificationsUnread = notifications.filter(n => !n.read).length
    },
    ADD_NOTIFICATION(state, notification) {
      state.notifications = [notification, ...state.notifications]
      if (!notification.read) {
        state.notificationsUnread++
      }
    },
    MARK_NOTIFICATION_READ(state, notificationId) {
      state.notifications = state.notifications.map(n =>
        n.id === notificationId ? { ...n, read: true } : n
      )
      state.notificationsUnread = state.notifications.filter(n => !n.read).length
    },
    MARK_ALL_NOTIFICATIONS_READ(state) {
      state.notifications = state.notifications.map(n => ({ ...n, read: true }))
      state.notificationsUnread = 0
    },
    SET_SELECTED_CARD(state, { card, listId }) {
      state.selectedCard = card
      state.selectedListId = listId
    },
    SET_UPLOAD_PROGRESS(state, { id, progress }) {
      state.uploadProgress = { ...state.uploadProgress, [id]: progress }
    },
    CLEAR_UPLOAD_PROGRESS(state, id) {
      const { [id]: _, ...rest } = state.uploadProgress
      state.uploadProgress = rest
    }
  },
  actions: {
    async subscribeLists({ commit, state }) {
      if (hasListener(LIST_LISTENER_KEY)) {
        return
      }

      commit('SET_LOADING', true)
      const q = query(collection(db, 'lists'), orderBy('order', 'asc'))

      const unsubscribe = onSnapshot(q, (querySnapshot) => {
        const listPromises = querySnapshot.docs.map(async (listDoc) => {
          const listData = { id: listDoc.id, ...listDoc.data() }

          return new Promise((resolve) => {
            const cardsQ = query(
              collection(db, 'lists', listDoc.id, 'cards'),
              orderBy('order', 'asc')
            )

            onSnapshot(cardsQ, (cardsSnap) => {
              const cards = cardsSnap.docs.map(cardDoc => ({
                id: cardDoc.id,
                ...cardDoc.data()
              }))
              listData.cards = cards
              resolve(listData)
            })
          })
        })

        Promise.all(listPromises).then((lists) => {
          commit('SET_LISTS', lists)
          commit('SET_LOADING', false)
        })
      }, (error) => {
        console.error('Error subscribing to lists:', error)
        commit('SET_LOADING', false)
      })

      addListener(LIST_LISTENER_KEY, unsubscribe)
    },
    unsubscribeLists() {
      if (hasListener(LIST_LISTENER_KEY)) {
        removeListener(LIST_LISTENER_KEY)
      }
    },
    async addList({ commit, state }, { title }) {
      try {
        const order = state.lists.length
        const docRef = await addDoc(collection(db, 'lists'), {
          title,
          order,
          createdAt: serverTimestamp()
        })
        const newList = {
          id: docRef.id,
          title,
          order,
          cards: []
        }
        commit('ADD_LIST', newList)

        logActivity({
          type: ACTIVITY_TYPES.LIST_CREATED,
          userId: CURRENT_USER.id,
          userName: CURRENT_USER.name,
          listId: docRef.id,
          data: { listTitle: title }
        })
      } catch (error) {
        console.error('Error adding list:', error)
      }
    },
    async updateList({ commit }, { id, updates }) {
      try {
        await updateDoc(doc(db, 'lists', id), updates)
        commit('UPDATE_LIST', { id, updates })
      } catch (error) {
        console.error('Error updating list:', error)
      }
    },
    async deleteList({ commit }, id) {
      try {
        await deleteDoc(doc(db, 'lists', id))
        commit('DELETE_LIST', id)
      } catch (error) {
        console.error('Error deleting list:', error)
      }
    },
    async addCard({ commit, state }, { listId, title }) {
      try {
        const list = state.lists.find(l => l.id === listId)
        const order = list && list.cards ? list.cards.length : 0

        const docRef = await addDoc(collection(db, 'lists', listId, 'cards'), {
          title,
          order,
          description: '',
          attachments: [],
          comments: [],
          createdAt: serverTimestamp()
        })

        const newCard = {
          id: docRef.id,
          title,
          order,
          description: '',
          attachments: [],
          comments: []
        }
        commit('ADD_CARD', { listId, card: newCard })

        logActivity({
          type: ACTIVITY_TYPES.CARD_CREATED,
          userId: CURRENT_USER.id,
          userName: CURRENT_USER.name,
          listId,
          cardId: docRef.id,
          data: { cardTitle: title }
        })
      } catch (error) {
        console.error('Error adding card:', error)
      }
    },
    async updateCard({ commit }, { listId, cardId, updates }) {
      try {
        await updateDoc(doc(db, 'lists', listId, 'cards', cardId), updates)
        commit('UPDATE_CARD', { listId, cardId, updates })
      } catch (error) {
        console.error('Error updating card:', error)
      }
    },
    async deleteCard({ commit }, { listId, cardId }) {
      try {
        await deleteDoc(doc(db, 'lists', listId, 'cards', cardId))
        commit('DELETE_CARD', { listId, cardId })
      } catch (error) {
        console.error('Error deleting card:', error)
      }
    },
    async moveCard({ commit, state }, { cardId, fromListId, toListId, card, newOrder }) {
      const fromList = state.lists.find(l => l.id === fromListId)
      const toList = state.lists.find(l => l.id === toListId)
      const cardToMove = card || fromList?.cards?.find(c => c.id === cardId)

      if (!cardToMove) return

      commit('MOVE_CARD', { cardId, fromListId, toListId, card: cardToMove, newOrder })

      try {
        await addDoc(collection(db, 'lists', toListId, 'cards'), {
          ...cardToMove,
          order: newOrder,
          movedAt: serverTimestamp()
        })

        await deleteDoc(doc(db, 'lists', fromListId, 'cards', cardId))

        logActivity({
          type: ACTIVITY_TYPES.CARD_MOVED,
          userId: CURRENT_USER.id,
          userName: CURRENT_USER.name,
          listId: toListId,
          cardId,
          data: {
            cardTitle: cardToMove.title,
            fromListTitle: fromList?.title,
            toListTitle: toList?.title
          }
        })
      } catch (error) {
        console.error('Error moving card in Firestore:', error)
      }
    },
    async uploadCardAttachment({ commit }, { listId, cardId, file }) {
      const uploadId = `upload_${Date.now()}`
      commit('SET_UPLOAD_PROGRESS', { id: uploadId, progress: 0 })

      try {
        const attachment = await uploadAttachment({
          file,
          listId,
          cardId,
          onProgress: (progress) => {
            commit('SET_UPLOAD_PROGRESS', { id: uploadId, progress })
          },
          userId: CURRENT_USER.id
        })

        await updateDoc(doc(db, 'lists', listId, 'cards', cardId), {
          attachments: arrayUnion(attachment)
        })

        commit('ADD_ATTACHMENT', { listId, cardId, attachment })

        logActivity({
          type: ACTIVITY_TYPES.ATTACHMENT_UPLOADED,
          userId: CURRENT_USER.id,
          userName: CURRENT_USER.name,
          listId,
          cardId,
          data: {
            fileName: attachment.name,
            cardTitle: ''
          }
        })

        return attachment
      } catch (error) {
        console.error('Error uploading attachment:', error)
        throw error
      } finally {
        commit('CLEAR_UPLOAD_PROGRESS', uploadId)
      }
    },
    async deleteCardAttachment({ commit }, { listId, cardId, attachment }) {
      try {
        await deleteAttachment(attachment.path)

        await updateDoc(doc(db, 'lists', listId, 'cards', cardId), {
          attachments: arrayRemove(attachment)
        })

        commit('DELETE_ATTACHMENT', { listId, cardId, attachmentId: attachment.id })

        logActivity({
          type: ACTIVITY_TYPES.ATTACHMENT_DELETED,
          userId: CURRENT_USER.id,
          userName: CURRENT_USER.name,
          listId,
          cardId,
          data: { fileName: attachment.name }
        })
      } catch (error) {
        console.error('Error deleting attachment:', error)
      }
    },
    async addCardComment({ commit, state }, { listId, cardId, content }) {
      try {
        const list = state.lists.find(l => l.id === listId)
        const card = list?.cards?.find(c => c.id === cardId)

        const { mentionedUserIds } = extractMentions(content, [CURRENT_USER])

        const comment = {
          id: `comment_${Date.now()}`,
          content,
          userId: CURRENT_USER.id,
          userName: CURRENT_USER.name,
          createdAt: new Date(),
          mentionedUserIds
        }

        await updateDoc(doc(db, 'lists', listId, 'cards', cardId), {
          comments: arrayUnion(comment)
        })

        commit('ADD_COMMENT', { listId, cardId, comment })

        logActivity({
          type: ACTIVITY_TYPES.COMMENT_ADDED,
          userId: CURRENT_USER.id,
          userName: CURRENT_USER.name,
          listId,
          cardId,
          mentionedUserIds,
          data: { cardTitle: card?.title }
        })

        if (mentionedUserIds.length > 0) {
          logActivity({
            type: ACTIVITY_TYPES.MENTIONED,
            userId: CURRENT_USER.id,
            userName: CURRENT_USER.name,
            listId,
            cardId,
            mentionedUserIds,
            data: {
              cardTitle: card?.title,
              commentPreview: content.substring(0, 50),
              mentionedName: '被@用户'
            }
          })
        }

        return comment
      } catch (error) {
        console.error('Error adding comment:', error)
      }
    },
    async deleteCardComment({ commit }, { listId, cardId, comment }) {
      try {
        await updateDoc(doc(db, 'lists', listId, 'cards', cardId), {
          comments: arrayRemove(comment)
        })

        commit('DELETE_COMMENT', { listId, cardId, commentId: comment.id })
      } catch (error) {
        console.error('Error deleting comment:', error)
      }
    },
    selectCard({ commit }, { card, listId }) {
      commit('SET_SELECTED_CARD', { card, listId })
    },
    clearSelectedCard({ commit }) {
      commit('SET_SELECTED_CARD', { card: null, listId: null })
    },
    async subscribeNotifications({ commit }, userId) {
      if (hasListener(NOTIFICATION_LISTENER_KEY)) {
        return
      }

      const q = query(
        collection(db, 'activity_logs'),
        where('mentionedUserIds', 'array-contains', userId || CURRENT_USER.id),
        orderBy('createdAt', 'desc')
      )

      const unsubscribe = onSnapshot(q, (snapshot) => {
        const notifications = snapshot.docs.map(doc => ({
          id: doc.id,
          ...doc.data(),
          createdAt: doc.data().createdAt?.toDate?.() || doc.data().createdAt,
          timeAgo: formatTimeAgo(doc.data().createdAt?.toDate?.() || doc.data().createdAt)
        }))
        commit('SET_NOTIFICATIONS', notifications)
      })

      addListener(NOTIFICATION_LISTENER_KEY, unsubscribe)
    },
    unsubscribeNotifications() {
      if (hasListener(NOTIFICATION_LISTENER_KEY)) {
        removeListener(NOTIFICATION_LISTENER_KEY)
      }
    },
    async markNotificationRead({ commit }, notificationId) {
      try {
        await updateDoc(doc(db, 'activity_logs', notificationId), { read: true })
        commit('MARK_NOTIFICATION_READ', notificationId)
      } catch (error) {
        console.error('Error marking notification read:', error)
      }
    },
    async markAllNotificationsRead({ commit, state }) {
      try {
        const unread = state.notifications.filter(n => !n.read)
        for (const notification of unread) {
          await updateDoc(doc(db, 'activity_logs', notification.id), { read: true })
        }
        commit('MARK_ALL_NOTIFICATIONS_READ')
      } catch (error) {
        console.error('Error marking all notifications read:', error)
      }
    }
  }
})
