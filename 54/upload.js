import { storage } from './firebase'
import {
  ref,
  uploadBytes,
  getDownloadURL,
  deleteObject,
  uploadBytesResumable
} from 'firebase/storage'

const MAX_FILE_SIZE = 10 * 1024 * 1024

const ACCEPTED_TYPES = [
  'image/jpeg',
  'image/png',
  'image/gif',
  'image/webp',
  'application/pdf',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/vnd.ms-excel',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  'text/plain'
]

function generateFileId() {
  return Date.now().toString(36) + Math.random().toString(36).substr(2)
}

function getFileExtension(filename) {
  const parts = filename.split('.')
  return parts.length > 1 ? parts[parts.length - 1].toLowerCase() : ''
}

function isImageType(mimeType) {
  return mimeType.startsWith('image/')
}

function formatFileSize(bytes) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

async function uploadAttachment({
  file,
  listId,
  cardId,
  onProgress = null,
  userId = 'anonymous'
}) {
  if (!file || !listId || !cardId) {
    throw new Error('缺少必要参数')
  }

  if (file.size > MAX_FILE_SIZE) {
    throw new Error(`文件大小不能超过 ${formatFileSize(MAX_FILE_SIZE)}`)
  }

  if (!ACCEPTED_TYPES.includes(file.type) && file.type !== '') {
    throw new Error('不支持的文件类型')
  }

  const fileId = generateFileId()
  const ext = getFileExtension(file.name) || (file.type.split('/')[1] || '')
  const path = `attachments/${listId}/${cardId}/${fileId}${ext ? '.' + ext : ''}`
  const storageRef = ref(storage, path)

  const metadata = {
    contentType: file.type || 'application/octet-stream',
    customMetadata: {
      originalName: file.name,
      fileSize: file.size.toString(),
      uploadedBy: userId,
      uploadedAt: new Date().toISOString()
    }
  }

  return new Promise((resolve, reject) => {
    const uploadTask = uploadBytesResumable(storageRef, file, metadata)

    uploadTask.on('state_changed',
      (snapshot) => {
        if (onProgress) {
          const progress = (snapshot.bytesTransferred / snapshot.totalBytes) * 100
          onProgress(progress)
        }
      },
      (error) => {
        reject(error)
      },
      async () => {
        try {
          const downloadURL = await getDownloadURL(uploadTask.snapshot.ref)
          resolve({
            id: fileId,
            name: file.name,
            type: file.type,
            size: file.size,
            sizeFormatted: formatFileSize(file.size),
            url: downloadURL,
            path,
            isImage: isImageType(file.type),
            uploadedAt: new Date()
          })
        } catch (error) {
          reject(error)
        }
      }
    )
  })
}

async function deleteAttachment(path) {
  if (!path) return

  try {
    const storageRef = ref(storage, path)
    await deleteObject(storageRef)
    return true
  } catch (error) {
    console.error('删除附件失败:', error)
    return false
  }
}

async function uploadMultipleAttachments({
  files,
  listId,
  cardId,
  onProgress = null,
  onFileComplete = null,
  userId = 'anonymous'
}) {
  const results = []
  const errors = []

  for (let i = 0; i < files.length; i++) {
    const file = files[i]
    try {
      const result = await uploadAttachment({
        file,
        listId,
        cardId,
        onProgress: (progress) => {
          if (onProgress) {
            onProgress({
              fileIndex: i,
              fileName: file.name,
              progress
            })
          }
        },
        userId
      })
      results.push(result)
      if (onFileComplete) {
        onFileComplete({ fileIndex: i, fileName: file.name, result })
      }
    } catch (error) {
      errors.push({ file, error: error.message })
    }
  }

  return { results, errors }
}

export {
  uploadAttachment,
  deleteAttachment,
  uploadMultipleAttachments,
  formatFileSize,
  isImageType,
  MAX_FILE_SIZE,
  ACCEPTED_TYPES
}
