module Auth where

import Data.ByteString (ByteString)
import Data.Text (Text, pack)
import Data.Time
import Database.SQLite.Simple
import Models
import System.Random
import Data.Text.Encoding (encodeUtf8, decodeUtf8)
import Data.Maybe (listToMaybe)

generateApiKey :: IO Text
generateApiKey = do
  gen <- getStdGen
  let chars = ['a'..'z'] ++ ['A'..'Z'] ++ ['0'..'9']
      key = take 32 $ randomRs (0, length chars - 1) gen
  return $ pack $ map (chars !!) key

createApiKey :: Connection -> Text -> IO ApiKey
createApiKey conn name = do
  now <- getCurrentTime
  key <- generateUniqueApiKey conn
  let apiKey = ApiKey 0 key name now Nothing
  execute conn "INSERT INTO api_keys (key, name, created_at, last_used_at) VALUES (?, ?, ?, ?)"
    (akKey apiKey, akName apiKey, utcTimeToText $ akCreatedAt apiKey, Nothing :: Maybe Text)
  lastId <- lastInsertRowId conn
  return apiKey { akId = fromIntegral lastId }
  where
    generateUniqueApiKey conn = do
      key <- generateApiKey
      existing <- query conn "SELECT key FROM api_keys WHERE key = ?" (Only key) :: IO [Only Text]
      if null existing
        then return key
        else generateUniqueApiKey conn

validateApiKey :: Connection -> Text -> IO (Maybe ApiKey)
validateApiKey conn key = do
  results <- query conn "SELECT id, key, name, created_at, last_used_at FROM api_keys WHERE key = ?" (Only key)
  case results of
    [apiKey] -> do
      now <- getCurrentTime
      execute conn "UPDATE api_keys SET last_used_at = ? WHERE id = ?" (utcTimeToText now, akId apiKey)
      return $ Just apiKey
    _ -> return Nothing

getAllApiKeys :: Connection -> IO [ApiKey]
getAllApiKeys conn = do
  query_ conn "SELECT id, key, name, created_at, last_used_at FROM api_keys ORDER BY created_at DESC"

getApiKeyById :: Connection -> Int -> IO (Maybe ApiKey)
getApiKeyById conn akId = do
  results <- query conn "SELECT id, key, name, created_at, last_used_at FROM api_keys WHERE id = ?" (Only akId)
  return $ listToMaybe results

deleteApiKey :: Connection -> Int -> IO Bool
deleteApiKey conn akId = do
  execute conn "DELETE FROM api_keys WHERE id = ?" (Only akId)
  changes <- changes conn
  return $ changes > 0

extractApiKeyFromHeader :: Maybe ByteString -> Maybe Text
extractApiKeyFromHeader Nothing = Nothing
extractApiKeyFromHeader (Just header) =
  let headerStr = decodeUtf8 header
      parts = words headerStr
  in case parts of
    ["Bearer", key] -> Just key
    ["ApiKey", key] -> Just key
    [key] -> Just key
    _ -> Nothing
