module Api where

import Data.Text (Text)
import Models
import Servant

type NoteApi =
  "api" :> "notes" :> Get '[JSON] [Note]
  :<|> "api" :> "notes" :> Capture "id" Int :> Get '[JSON] Note
  :<|> "api" :> "notes" :> ReqBody '[JSON] NoteRequest :> Post '[JSON] Note
  :<|> "api" :> "notes" :> Capture "id" Int :> ReqBody '[JSON] NoteRequest :> Put '[JSON] Note
  :<|> "api" :> "notes" :> Capture "id" Int :> Delete '[JSON] ()
  :<|> "api" :> "notes" :> "search" :> QueryParam "q" Text :> Get '[JSON] [Note]
  :<|> "api" :> "share" :> ReqBody '[JSON] ShareLinkRequest :> Post '[JSON] ShareLink
  :<|> "api" :> "share" :> Capture "id" Int :> Get '[JSON] Note
  :<|> "api" :> "share" :> "code" :> Capture "code" Text :> Get '[JSON] Note
  :<|> "api" :> "share" :> Capture "id" Int :> Delete '[JSON] ()
  :<|> "api" :> "notes" :> Capture "id" Int :> "shares" :> Get '[JSON] [ShareLink]
  :<|> "api" :> "auth" :> "keys" :> ReqBody '[JSON] ApiKeyRequest :> Post '[JSON] ApiKey
  :<|> "api" :> "auth" :> "keys" :> Get '[JSON] [ApiKey]
  :<|> "api" :> "auth" :> "keys" :> Capture "id" Int :> Delete '[JSON] ()

noteApi :: Proxy NoteApi
noteApi = Proxy
