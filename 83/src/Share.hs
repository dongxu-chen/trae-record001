module Share where

import Data.Text (Text, pack)
import Data.Time
import Database.SQLite.Simple
import Models
import System.Random

generateShortCode :: Int -> IO Text
generateShortCode length = do
  gen <- getStdGen
  let chars = ['a'..'z'] ++ ['A'..'Z'] ++ ['0'..'9']
      code = take length $ randomRs (0, length chars - 1) gen
  return $ pack $ map (chars !!) code

createShareLink :: Connection -> Int -> Maybe Int -> IO (Maybe ShareLink)
createShareLink conn noteId expiresInDays = do
  noteExists <- query conn "SELECT id FROM notes WHERE id = ?" (Only noteId) :: IO [Only Int]
  if null noteExists
    then return Nothing
    else do
      now <- getCurrentTime
      shortCode <- generateUniqueShortCode conn
      let expiresAt = fmap (\days -> addUTCTime (fromIntegral $ days * 86400) now) expiresInDays
          share = ShareLink 0 noteId shortCode expiresAt now
      execute conn "INSERT INTO share_links (note_id, short_code, expires_at, created_at) VALUES (?, ?, ?, ?)"
        (shareNoteId share, shareShortCode share, utcTimeToText <$> shareExpiresAt share, utcTimeToText $ shareCreatedAt share)
      lastId <- lastInsertRowId conn
      return $ Just share { shareId = fromIntegral lastId }
  where
    generateUniqueShortCode conn = do
      code <- generateShortCode 8
      existing <- query conn "SELECT short_code FROM share_links WHERE short_code = ?" (Only code) :: IO [Only Text]
      if null existing
        then return code
        else generateUniqueShortCode conn

getShareLinkByShortCode :: Connection -> Text -> IO (Maybe ShareLink)
getShareLinkByShortCode conn shortCode = do
  now <- getCurrentTime
  results <- query conn "SELECT id, note_id, short_code, expires_at, created_at FROM share_links WHERE short_code = ?" (Only shortCode)
  case results of
    [share] ->
      case shareExpiresAt share of
        Nothing -> return $ Just share
        Just expiresAt ->
          if expiresAt > now
            then return $ Just share
            else return Nothing
    _ -> return Nothing

getShareLinkById :: Connection -> Int -> IO (Maybe ShareLink)
getShareLinkById conn shareId = do
  now <- getCurrentTime
  results <- query conn "SELECT id, note_id, short_code, expires_at, created_at FROM share_links WHERE id = ?" (Only shareId)
  case results of
    [share] ->
      case shareExpiresAt share of
        Nothing -> return $ Just share
        Just expiresAt ->
          if expiresAt > now
            then return $ Just share
            else return Nothing
    _ -> return Nothing

getShareLinksByNoteId :: Connection -> Int -> IO [ShareLink]
getShareLinksByNoteId conn noteId = do
  now <- getCurrentTime
  allShares <- query conn "SELECT id, note_id, short_code, expires_at, created_at FROM share_links WHERE note_id = ? ORDER BY created_at DESC" (Only noteId)
  return $ filter isValid allShares
  where
    isValid share = case shareExpiresAt share of
      Nothing -> True
      Just expiresAt -> expiresAt > now

deleteShareLink :: Connection -> Int -> IO Bool
deleteShareLink conn shareId = do
  execute conn "DELETE FROM share_links WHERE id = ?" (Only shareId)
  changes <- changes conn
  return $ changes > 0
