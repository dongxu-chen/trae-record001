import { Client } from '@elastic/elasticsearch'

const ELASTICSEARCH_NODE = process.env.ELASTICSEARCH_NODE || 'http://localhost:9200'
const ELASTICSEARCH_USERNAME = process.env.ELASTICSEARCH_USERNAME || 'elastic'
const ELASTICSEARCH_PASSWORD = process.env.ELASTICSEARCH_PASSWORD || 'changeme'

const client = new Client({
  node: ELASTICSEARCH_NODE,
  auth: {
    username: ELASTICSEARCH_USERNAME,
    password: ELASTICSEARCH_PASSWORD,
  },
  tls: {
    rejectUnauthorized: false,
  },
})

export const NOTES_INDEX = 'notes'

export async function createNotesIndex() {
  try {
    const indexExists = await client.indices.exists({ index: NOTES_INDEX })
    
    if (!indexExists) {
      await client.indices.create({
        index: NOTES_INDEX,
        body: {
          settings: {
            analysis: {
              analyzer: {
                ik_smart: {
                  type: 'ik',
                  use_smart: true,
                },
                ik_max_word: {
                  type: 'ik',
                  use_smart: false,
                },
              },
            },
          },
          mappings: {
            properties: {
              title: {
                type: 'text',
                analyzer: 'ik_max_word',
                search_analyzer: 'ik_smart',
              },
              content: {
                type: 'text',
                analyzer: 'ik_max_word',
                search_analyzer: 'ik_smart',
              },
              tags: {
                type: 'keyword',
              },
              folderId: {
                type: 'keyword',
              },
              createdAt: {
                type: 'date',
              },
              updatedAt: {
                type: 'date',
              },
            },
          },
        },
      })
      console.log(`Index '${NOTES_INDEX}' created successfully')
    }
  } catch (error) {
    console.error('Error creating index:', error)
  }
}

export async function indexNote(note: {
  _id: string
  title: string
  content: string
  tags: string[]
  folderId?: string
  createdAt: Date
  updatedAt: Date
}) {
  try {
    await client.index({
      index: NOTES_INDEX,
      id: note._id,
      body: {
        title: note.title,
        content: note.content,
        tags: note.tags,
        folderId: note.folderId,
        createdAt: note.createdAt,
        updatedAt: note.updatedAt,
      },
    })
  } catch (error) {
    console.error('Error indexing note:', error)
  }
}

export async function updateNoteInIndex(note: {
  _id: string
  title: string
  content: string
  tags: string[]
  folderId?: string
  updatedAt: Date
}) {
  try {
    await client.update({
      index: NOTES_INDEX,
      id: note._id,
      body: {
        doc: {
          title: note.title,
          content: note.content,
          tags: note.tags,
          folderId: note.folderId,
          updatedAt: note.updatedAt,
        },
      },
    })
  } catch (error) {
    console.error('Error updating note in index:', error)
  }
}

export async function deleteNoteFromIndex(noteId: string) {
  try {
    await client.delete({
      index: NOTES_INDEX,
      id: noteId,
    })
  } catch (error) {
    console.error('Error deleting note from index:', error)
  }
}

export async function searchNotes(query: string, tags?: string[], folderId?: string) {
  try {
    const must: any[] = [
      {
        multi_match: {
          query,
          fields: ['title^3', 'content'],
          analyzer: 'ik_smart',
        },
      },
    ]

    const filter: any[] = []

    if (tags && tags.length > 0) {
      filter.push({
        terms: {
          tags,
        },
      })
    }

    if (folderId) {
      filter.push({
        term: {
          folderId,
        },
      })
    }

    const response = await client.search({
      index: NOTES_INDEX,
      body: {
        query: {
          bool: {
            must,
            filter,
          },
        },
        highlight: {
          fields: {
            title: {},
            content: {},
          },
        },
      },
    })

    return response.hits.hits.map((hit: any) => ({
      _id: hit._id,
      ...hit._source,
      highlight: hit.highlight,
    }))
  } catch (error) {
    console.error('Error searching notes:', error)
    return []
  }
}

export default client
