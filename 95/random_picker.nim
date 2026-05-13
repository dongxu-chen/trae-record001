import random, json, locks

var
  randLock: Lock
  randInitialized {.global.}: bool = false

type
  Joke* = object
    id*: int
    category*: string
    question*: string
    answer*: string
    votes*: int

proc initRandom*() =
  if not randInitialized:
    initLock(randLock)
    withLock randLock:
      if not randInitialized:
        randomize()
        randInitialized = true

proc parseJokes*(jsonStr: string): seq[Joke] =
  let jsonData = parseJson(jsonStr)
  let jokesArray = jsonData["jokes"]
  
  for jokeNode in jokesArray:
    let votes = if jokeNode.hasKey("votes"): jokeNode["votes"].getInt() else: 0
    let joke = Joke(
      id: jokeNode["id"].getInt(),
      category: jokeNode["category"].getStr(),
      question: jokeNode["question"].getStr(),
      answer: jokeNode["answer"].getStr(),
      votes: votes
    )
    result.add(joke)

proc pickRandom*[T](items: seq[T]): T =
  if items.len == 0:
    raise newException(ValueError, "Cannot pick from empty sequence")
  
  if not randInitialized:
    initRandom()
  
  withLock randLock:
    let index = rand(items.len - 1)
    return items[index]

proc pickRandomByCategory*(jokes: seq[Joke], category: string): Joke =
  let filtered = jokes.filter(j => j.category == category)
  if filtered.len == 0:
    raise newException(ValueError, "No jokes found in category: " & category)
  return pickRandom(filtered)

proc toJson*(joke: Joke, includeVotes: bool = true): JsonNode =
  result = %*{
    "id": joke.id,
    "category": joke.category,
    "question": joke.question,
    "answer": joke.answer
  }
  if includeVotes:
    result["votes"] = %joke.votes