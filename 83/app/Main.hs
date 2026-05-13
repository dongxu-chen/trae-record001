module Main where

import Api
import DB
import Handlers
import Network.Wai
import Network.Wai.Handler.Warp
import Servant

app :: ConnectionPool -> Application
app pool = serve noteApi (noteServer pool)

main :: IO ()
main = do
  putStrLn "Starting Note API server on port 8080..."
  pool <- initDB
  run 8080 (app pool)
