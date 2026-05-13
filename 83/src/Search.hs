module Search where

import Data.Text (Text)
import Database.SQLite.Simple
import Models

searchNotes :: Connection -> Text -> IO [Note]
searchNotes conn query = do
  results <- query conn "SELECT n.id, n.title, n.content, n.created_at, n.updated_at FROM notes n JOIN notes_fts fts ON n.id = fts.rowid WHERE fts MATCH ? ORDER BY rank" (Only query)
  return results

updateSearchIndex :: Connection -> Int -> Text -> Text -> IO ()
updateSearchIndex conn noteId title content = do
  existing <- query conn "SELECT rowid FROM notes_fts WHERE rowid = ?" (Only noteId) :: IO [Only Int]
  if null existing
    then execute conn "INSERT INTO notes_fts(rowid, title, content) VALUES (?, ?, ?)" (noteId, title, content)
    else execute conn "UPDATE notes_fts SET title = ?, content = ? WHERE rowid = ?" (title, content, noteId)

deleteFromSearchIndex :: Connection -> Int -> IO ()
deleteFromSearchIndex conn noteId = do
  execute conn "DELETE FROM notes_fts WHERE rowid = ?" (Only noteId)
