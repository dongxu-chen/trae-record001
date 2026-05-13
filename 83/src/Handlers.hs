module Handlers where

import Control.Exception (SomeException, try)
import Data.Text (Text)
import DB
import Models
import Servant
import Servant.Server
import Database.SQLite.Simple (withTransaction, Connection)
import qualified Data.Pool as Pool
import qualified Share as S
import qualified Search as Se
import qualified Auth as A

withConnection :: ConnectionPool -> (Connection -> IO a) -> Handler a
withConnection pool action = do
  result <- liftIO $ try $ Pool.withResource pool action
  case result of
    Left (e :: SomeException) -> throwError err500 { errBody = "Database error" }
    Right x -> return x

withTransactionConnection :: ConnectionPool -> (Connection -> IO a) -> Handler a
withTransactionConnection pool action = do
  result <- liftIO $ try $ Pool.withResource pool $ \conn ->
    withTransaction conn (action conn)
  case result of
    Left (e :: SomeException) -> throwError err500 { errBody = "Database error" }
    Right x -> return x

noteServer :: ConnectionPool -> Server NoteApi
noteServer pool =
  listNotes
  :<|> getNote
  :<|> createNoteHandler
  :<|> updateNoteHandler
  :<|> deleteNoteHandler
  :<|> searchNotesHandler
  :<|> createShareHandler
  :<|> getNoteByShareId
  :<|> getNoteByShortCode
  :<|> deleteShareHandler
  :<|> getSharesByNoteId
  :<|> createApiKeyHandler
  :<|> listApiKeysHandler
  :<|> deleteApiKeyHandler
  where
    listNotes :: Handler [Note]
    listNotes = withConnection pool getAllNotes

    getNote :: Int -> Handler Note
    getNote nid = do
      maybeNote <- withConnection pool $ \conn -> getNoteById conn nid
      case maybeNote of
        Nothing -> throwError err404
        Just note -> return note

    createNoteHandler :: NoteRequest -> Handler Note
    createNoteHandler nr = withTransactionConnection pool $ \conn -> do
      note <- createNote conn nr
      Se.updateSearchIndex conn (noteId note) (noteTitle note) (noteContent note)
      return note

    updateNoteHandler :: Int -> NoteRequest -> Handler Note
    updateNoteHandler nid nr = do
      maybeNote <- withTransactionConnection pool $ \conn -> do
        updated <- updateNote conn nid nr
        case updated of
          Nothing -> return Nothing
          Just note -> do
            Se.updateSearchIndex conn (noteId note) (noteTitle note) (noteContent note)
            return $ Just note
      case maybeNote of
        Nothing -> throwError err404
        Just note -> return note

    deleteNoteHandler :: Int -> Handler ()
    deleteNoteHandler nid = do
      success <- withTransactionConnection pool $ \conn -> do
        deleted <- deleteNote conn nid
        if deleted
          then do
            Se.deleteFromSearchIndex conn nid
            return True
          else return False
      if success
        then return ()
        else throwError err404

    searchNotesHandler :: Maybe Text -> Handler [Note]
    searchNotesHandler Nothing = return []
    searchNotesHandler (Just query) = withConnection pool $ \conn -> Se.searchNotes conn query

    createShareHandler :: ShareLinkRequest -> Handler ShareLink
    createShareHandler slr = do
      maybeShare <- withTransactionConnection pool $ \conn ->
        S.createShareLink conn (slrNoteId slr) (slrExpiresInDays slr)
      case maybeShare of
        Nothing -> throwError err404
        Just share -> return share

    getNoteByShareId :: Int -> Handler Note
    getNoteByShareId shareId = do
      maybeNote <- withConnection pool $ \conn -> do
        maybeShare <- S.getShareLinkById conn shareId
        case maybeShare of
          Nothing -> return Nothing
          Just share -> getNoteById conn (shareNoteId share)
      case maybeNote of
        Nothing -> throwError err404
        Just note -> return note

    getNoteByShortCode :: Text -> Handler Note
    getNoteByShortCode shortCode = do
      maybeNote <- withConnection pool $ \conn -> do
        maybeShare <- S.getShareLinkByShortCode conn shortCode
        case maybeShare of
          Nothing -> return Nothing
          Just share -> getNoteById conn (shareNoteId share)
      case maybeNote of
        Nothing -> throwError err404
        Just note -> return note

    deleteShareHandler :: Int -> Handler ()
    deleteShareHandler shareId = do
      success <- withTransactionConnection pool $ \conn -> S.deleteShareLink conn shareId
      if success
        then return ()
        else throwError err404

    getSharesByNoteId :: Int -> Handler [ShareLink]
    getSharesByNoteId noteId = withConnection pool $ \conn -> S.getShareLinksByNoteId conn noteId

    createApiKeyHandler :: ApiKeyRequest -> Handler ApiKey
    createApiKeyHandler akr = withTransactionConnection pool $ \conn -> A.createApiKey conn (akrName akr)

    listApiKeysHandler :: Handler [ApiKey]
    listApiKeysHandler = withConnection pool A.getAllApiKeys

    deleteApiKeyHandler :: Int -> Handler ()
    deleteApiKeyHandler akId = do
      success <- withTransactionConnection pool $ \conn -> A.deleteApiKey conn akId
      if success
        then return ()
        else throwError err404
