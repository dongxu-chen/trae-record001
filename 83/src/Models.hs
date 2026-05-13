module Models where

import Data.Aeson
import Data.Text (Text, pack, unpack)
import Data.Time
import Data.Time.Format
import Database.SQLite.Simple
import Database.SQLite.Simple.FromRow
import Database.SQLite.Simple.ToRow
import Database.SQLite.Simple.FromField
import Database.SQLite.Simple.ToField

data Note = Note
  { noteId :: Int
  , noteTitle :: Text
  , noteContent :: Text
  , noteCreatedAt :: UTCTime
  , noteUpdatedAt :: UTCTime
  } deriving (Show)

data NoteRequest = NoteRequest
  { nrTitle :: Text
  , nrContent :: Text
  } deriving (Show)

data ShareLink = ShareLink
  { shareId :: Int
  , shareNoteId :: Int
  , shareShortCode :: Text
  , shareExpiresAt :: Maybe UTCTime
  , shareCreatedAt :: UTCTime
  } deriving (Show)

data ShareLinkRequest = ShareLinkRequest
  { slrNoteId :: Int
  , slrExpiresInDays :: Maybe Int
  } deriving (Show)

data ApiKey = ApiKey
  { akId :: Int
  , akKey :: Text
  , akName :: Text
  , akCreatedAt :: UTCTime
  , akLastUsedAt :: Maybe UTCTime
  } deriving (Show)

data ApiKeyRequest = ApiKeyRequest
  { akrName :: Text
  } deriving (Show)

timeFormat :: String
timeFormat = "%Y-%m-%d %H:%M:%S%Q"

utcTimeToText :: UTCTime -> Text
utcTimeToText = pack . formatTime defaultTimeLocale timeFormat

textToUTCTime :: Text -> Maybe UTCTime
textToUTCTime = parseTimeM True defaultTimeLocale timeFormat . unpack

instance FromRow Note where
  fromRow = Note
    <$> field
    <*> field
    <*> field
    <*> (textToUTCTime <$> field)
    <*> (textToUTCTime <$> field)
    >>= \note ->
      case (noteCreatedAt note, noteUpdatedAt note) of
        (Just created, Just updated) -> return $ note { noteCreatedAt = created, noteUpdatedAt = updated }
        _ -> fail "Failed to parse time"

instance ToRow Note where
  toRow note =
    [ toField (noteId note)
    , toField (noteTitle note)
    , toField (noteContent note)
    , toField (utcTimeToText $ noteCreatedAt note)
    , toField (utcTimeToText $ noteUpdatedAt note)
    ]

instance ToJSON Note where
  toJSON note = object
    [ "id" .= noteId note
    , "title" .= noteTitle note
    , "content" .= noteContent note
    , "created_at" .= noteCreatedAt note
    , "updated_at" .= noteUpdatedAt note
    ]

instance FromJSON NoteRequest where
  parseJSON = withObject "NoteRequest" $ \v -> NoteRequest
    <$> v .: "title"
    <*> v .: "content"

instance ToJSON NoteRequest where
  toJSON nr = object
    [ "title" .= nrTitle nr
    , "content" .= nrContent nr
    ]

instance FromRow ShareLink where
  fromRow = ShareLink
    <$> field
    <*> field
    <*> field
    <*> ((>>= textToUTCTime) <$> field)
    <*> (textToUTCTime <$> field)
    >>= \share ->
      case shareCreatedAt share of
        Just created -> return $ share { shareCreatedAt = created }
        _ -> fail "Failed to parse time"

instance ToRow ShareLink where
  toRow share =
    [ toField (shareId share)
    , toField (shareNoteId share)
    , toField (shareShortCode share)
    , toField (utcTimeToText <$> shareExpiresAt share)
    , toField (utcTimeToText $ shareCreatedAt share)
    ]

instance ToJSON ShareLink where
  toJSON share = object
    [ "id" .= shareId share
    , "note_id" .= shareNoteId share
    , "short_code" .= shareShortCode share
    , "expires_at" .= shareExpiresAt share
    , "created_at" .= shareCreatedAt share
    ]

instance FromJSON ShareLinkRequest where
  parseJSON = withObject "ShareLinkRequest" $ \v -> ShareLinkRequest
    <$> v .: "note_id"
    <*> v .:? "expires_in_days"

instance ToJSON ShareLinkRequest where
  toJSON slr = object
    [ "note_id" .= slrNoteId slr
    , "expires_in_days" .= slrExpiresInDays slr
    ]

instance FromRow ApiKey where
  fromRow = ApiKey
    <$> field
    <*> field
    <*> field
    <*> (textToUTCTime <$> field)
    <*> ((>>= textToUTCTime) <$> field)
    >>= \ak ->
      case akCreatedAt ak of
        Just created -> return $ ak { akCreatedAt = created }
        _ -> fail "Failed to parse time"

instance ToRow ApiKey where
  toRow ak =
    [ toField (akId ak)
    , toField (akKey ak)
    , toField (akName ak)
    , toField (utcTimeToText $ akCreatedAt ak)
    , toField (utcTimeToText <$> akLastUsedAt ak)
    ]

instance ToJSON ApiKey where
  toJSON ak = object
    [ "id" .= akId ak
    , "key" .= akKey ak
    , "name" .= akName ak
    , "created_at" .= akCreatedAt ak
    , "last_used_at" .= akLastUsedAt ak
    ]

instance FromJSON ApiKeyRequest where
  parseJSON = withObject "ApiKeyRequest" $ \v -> ApiKeyRequest
    <$> v .: "name"

instance ToJSON ApiKeyRequest where
  toJSON akr = object
    [ "name" .= akrName akr
    ]

getAllNotes :: Connection -> IO [Note]
getAllNotes conn = query_ conn "SELECT id, title, content, created_at, updated_at FROM notes ORDER BY updated_at DESC"

getNoteById :: Connection -> Int -> IO (Maybe Note)
getNoteById conn nid = do
  results <- query conn "SELECT id, title, content, created_at, updated_at FROM notes WHERE id = ?" (Only nid)
  return $ case results of
    [note] -> Just note
    _ -> Nothing

createNote :: Connection -> NoteRequest -> IO Note
createNote conn nr = do
  now <- getCurrentTime
  let note = Note 0 (nrTitle nr) (nrContent nr) now now
  execute conn "INSERT INTO notes (title, content, created_at, updated_at) VALUES (?, ?, ?, ?)"
    (noteTitle note, noteContent note, utcTimeToText $ noteCreatedAt note, utcTimeToText $ noteUpdatedAt note)
  lastId <- lastInsertRowId conn
  return note { noteId = fromIntegral lastId }

updateNote :: Connection -> Int -> NoteRequest -> IO (Maybe Note)
updateNote conn nid nr = do
  existing <- getNoteById conn nid
  case existing of
    Nothing -> return Nothing
    Just oldNote -> do
      now <- getCurrentTime
      let updatedNote = oldNote
            { noteTitle = nrTitle nr
            , noteContent = nrContent nr
            , noteUpdatedAt = now
            }
      execute conn "UPDATE notes SET title = ?, content = ?, updated_at = ? WHERE id = ?"
        (noteTitle updatedNote, noteContent updatedNote, utcTimeToText $ noteUpdatedAt updatedNote, noteId updatedNote)
      return $ Just updatedNote

deleteNote :: Connection -> Int -> IO Bool
deleteNote conn nid = do
  execute conn "DELETE FROM notes WHERE id = ?" (Only nid)
  changes <- changes conn
  return $ changes > 0
