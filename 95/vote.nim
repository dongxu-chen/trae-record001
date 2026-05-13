import json, times, locks, os, strutils, tables

type
  Vote* = object
    jokeId*: int
    voterId*: string
    voteType*: int
    votedAt*: Time
  
  VoteStore* = object
    votes*: Table[int, Table[string, int]]
    totalVotes*: Table[int, int]
    filePath*: string
    lock*: Lock

proc newVoteStore*(filePath: string): VoteStore =
  result = VoteStore(
    votes: initTable[int, Table[string, int]](),
    totalVotes: initTable[int, int](),
    filePath: filePath,
    lock: initLock(result.lock)
  )
  if fileExists(filePath):
    result.loadFromFile()

proc saveToFile*(store: var VoteStore) =
  withLock store.lock:
    var votesArray = newJArray()
    
    for jokeId, voterMap in store.votes:
      for voterId, voteType in voterMap:
        votesArray.add(%*{
          "jokeId": jokeId,
          "voterId": voterId,
          "voteType": voteType
        })
    
    let jsonContent = %*{"votes": votesArray}
    writeFile(store.filePath, $jsonContent)

proc loadFromFile*(store: var VoteStore) =
  withLock store.lock:
    if not fileExists(store.filePath):
      return
    
    let content = readFile(store.filePath)
    let jsonData = parseJson(content)
    let votesArray = jsonData["votes"]
    
    for voteNode in votesArray:
      let jokeId = voteNode["jokeId"].getInt()
      let voterId = voteNode["voterId"].getStr()
      let voteType = voteNode["voteType"].getInt()
      
      if not store.votes.hasKey(jokeId):
        store.votes[jokeId] = initTable[string, int]()
      
      store.votes[jokeId][voterId] = voteType
      
      if not store.totalVotes.hasKey(jokeId):
        store.totalVotes[jokeId] = 0
      store.totalVotes[jokeId] += voteType

proc addVote*(store: var VoteStore, jokeId: int, voterId: string, voteType: int): bool =
  if voteType notin [-1, 1]:
    return false
  
  withLock store.lock:
    if not store.votes.hasKey(jokeId):
      store.votes[jokeId] = initTable[string, int]()
    
    let previousVote = store.votes[jokeId].getOrDefault(voterId, 0)
    
    if previousVote == voteType:
      return false
    
    if previousVote != 0:
      store.totalVotes[jokeId] -= previousVote
    
    store.votes[jokeId][voterId] = voteType
    
    if not store.totalVotes.hasKey(jokeId):
      store.totalVotes[jokeId] = 0
    store.totalVotes[jokeId] += voteType
    
    store.saveToFile()
    return true

proc getVoteCount*(store: VoteStore, jokeId: int): int =
  withLock store.lock:
    return store.totalVotes.getOrDefault(jokeId, 0)

proc getUserVote*(store: VoteStore, jokeId: int, voterId: string): int =
  withLock store.lock:
    if store.votes.hasKey(jokeId):
      return store.votes[jokeId].getOrDefault(voterId, 0)
    return 0

proc getTopJokes*(store: VoteStore, limit: int = 10): seq[(int, int)] =
  withLock store.lock:
    var jokeScores = newSeq[(int, int)]()
    for jokeId, score in store.totalVotes:
      jokeScores.add((jokeId, score))
    
    jokeScores.sort(proc(a, b: (int, int)): int = b[1] - a[1])
    
    if jokeScores.len > limit:
      jokeScores = jokeScores[0..<limit]
    
    return jokeScores

proc toJson*(store: VoteStore, jokeId: int): JsonNode =
  withLock store.lock:
    result = %*{
      "jokeId": jokeId,
      "totalVotes": store.totalVotes.getOrDefault(jokeId, 0)
    }