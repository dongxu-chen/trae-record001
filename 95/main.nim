import jester, json, strutils, os, tables
import logger, random_picker, rate_limit, submission, vote, admin

const
  JOKES_FILE = "jokes.json"
  SUBMISSIONS_FILE = "submissions.json"
  VOTES_FILE = "votes.json"
  ADMIN_FILE = "admin.json"
  MAX_REQUESTS_PER_MINUTE = 60
  TIME_WINDOW_SECONDS = 60

var
  jokes: seq[Joke]
  limiter: RateLimiter
  submissionStore: SubmissionStore
  voteStore: VoteStore
  adminStore: AdminStore
  nextJokeId: int

proc loadJokes(): seq[Joke] =
  if not fileExists(JOKES_FILE):
    raise newException(IOError, "Jokes file not found: " & JOKES_FILE)
  let content = readFile(JOKES_FILE)
  return parseJokes(content)

proc saveJokes() =
  var jokesArray = newJArray()
  for joke in jokes:
    jokesArray.add(%*{
      "id": joke.id,
      "category": joke.category,
      "question": joke.question,
      "answer": joke.answer,
      "votes": joke.votes
    })
  
  let jsonContent = %*{"jokes": jokesArray}
  writeFile(JOKES_FILE, $jsonContent)

proc getClientId(request: Request): string =
  let forwardedFor = request.headers.getOrDefault("X-Forwarded-For", "")
  let userAgent = request.headers.getOrDefault("User-Agent", "")
  return limiter.extractRealClientId(forwardedFor, request.clientIp, userAgent)

proc addRateLimitHeaders(response: var Response, limiter: RateLimiter, clientId: string) =
  response.headers["X-RateLimit-Limit"] = $limiter.maxRequests
  response.headers["X-RateLimit-Remaining"] = $limiter.getRemaining(clientId)
  
  let resetTime = limiter.getResetTime(clientId)
  if resetTime.isSome():
    response.headers["X-RateLimit-Reset"] = $resetTime.get()

proc getSessionId(request: Request): string =
  let authHeader = request.headers.getOrDefault("Authorization", "")
  if authHeader.startsWith("Bearer "):
    return authHeader[7..^1]
  return ""

proc requireAuth(request: Request): Option[string] =
  let sessionId = getSessionId(request)
  if sessionId == "":
    return none(string)
  return adminStore.validateSession(sessionId)

proc getJokeById(id: int): Option[Joke] =
  for joke in jokes:
    if joke.id == id:
      return some(joke)
  return none(Joke)

routes:
  get "/":
    let clientId = getClientId(request)
    info(fmt"GET / - Client: {clientId}")
    
    let responseData = %*{
      "api": "Random Jokes API",
      "version": "1.0.0",
      "endpoints": %*{
        "GET /": "This help message",
        "GET /joke": "Get a random joke",
        "GET /joke/:category": "Get a random joke from specific category",
        "GET /jokes/top": "Get top voted jokes",
        "GET /joke/:id/vote": "Get vote info for a joke",
        "POST /joke/:id/vote": "Vote for a joke (vote=1 or vote=-1)",
        "GET /categories": "List all available categories",
        "POST /jokes": "Submit a new joke for review",
        "GET /admin": "Admin panel",
        "POST /admin/login": "Admin login"
      }
    }
    
    resp Http200, responseData, "application/json"

  get "/joke":
    let clientId = getClientId(request)
    info(fmt"GET /joke - Client: {clientId}")
    
    if limiter.isRateLimited(clientId):
      warn(fmt"Rate limit exceeded for client: {clientId}")
      let errorResponse = %*{
        "error": "Rate limit exceeded",
        "message": fmt"Too many requests. Limit is {MAX_REQUESTS_PER_MINUTE} per minute."
      }
      addRateLimitHeaders(response, limiter, clientId)
      resp Http429, errorResponse, "application/json"
    
    let randomJoke = pickRandom(jokes)
    randomJoke.votes = voteStore.getVoteCount(randomJoke.id)
    debug(fmt"Selected joke ID: {randomJoke.id}")
    
    addRateLimitHeaders(response, limiter, clientId)
    resp Http200, randomJoke.toJson(), "application/json"

  get "/joke/@category":
    let category = @"category"
    let clientId = getClientId(request)
    info(fmt"GET /joke/{category} - Client: {clientId}")
    
    if limiter.isRateLimited(clientId):
      warn(fmt"Rate limit exceeded for client: {clientId}")
      let errorResponse = %*{
        "error": "Rate limit exceeded",
        "message": fmt"Too many requests. Limit is {MAX_REQUESTS_PER_MINUTE} per minute."
      }
      addRateLimitHeaders(response, limiter, clientId)
      resp Http429, errorResponse, "application/json"
    
    try:
      let randomJoke = pickRandomByCategory(jokes, category)
      randomJoke.votes = voteStore.getVoteCount(randomJoke.id)
      debug(fmt"Selected joke ID: {randomJoke.id} from category: {category}")
      addRateLimitHeaders(response, limiter, clientId)
      resp Http200, randomJoke.toJson(), "application/json"
    except ValueError:
      error(fmt"Category not found: {category}")
      let errorResponse = %*{
        "error": "Category not found",
        "message": fmt"No jokes found in category: {category}"
      }
      resp Http404, errorResponse, "application/json"

  get "/jokes/top":
    let clientId = getClientId(request)
    info(fmt"GET /jokes/top - Client: {clientId}")
    
    if limiter.isRateLimited(clientId):
      warn(fmt"Rate limit exceeded for client: {clientId}")
      let errorResponse = %*{
        "error": "Rate limit exceeded",
        "message": fmt"Too many requests. Limit is {MAX_REQUESTS_PER_MINUTE} per minute."
      }
      addRateLimitHeaders(response, limiter, clientId)
      resp Http429, errorResponse, "application/json"
    
    let limit = parseInt(request.params.getOrDefault("limit", "10"))
    let topJokes = voteStore.getTopJokes(limit)
    
    var resultArray = newJArray()
    for (jokeId, score) in topJokes:
      let jokeOpt = getJokeById(jokeId)
      if jokeOpt.isSome():
        let joke = jokeOpt.get()
        resultArray.add(%*{
          "id": joke.id,
          "category": joke.category,
          "question": joke.question,
          "answer": joke.answer,
          "votes": score
        })
    
    let responseData = %*{"jokes": resultArray}
    addRateLimitHeaders(response, limiter, clientId)
    resp Http200, responseData, "application/json"

  get "/joke/@id/vote":
    let jokeIdStr = @"id"
    let clientId = getClientId(request)
    info(fmt"GET /joke/{jokeIdStr}/vote - Client: {clientId}")
    
    let jokeId = parseInt(jokeIdStr)
    let totalVotes = voteStore.getVoteCount(jokeId)
    let userVote = voteStore.getUserVote(jokeId, clientId)
    
    let responseData = %*{
      "jokeId": jokeId,
      "totalVotes": totalVotes,
      "userVote": userVote
    }
    
    resp Http200, responseData, "application/json"

  post "/joke/@id/vote":
    let jokeIdStr = @"id"
    let clientId = getClientId(request)
    info(fmt"POST /joke/{jokeIdStr}/vote - Client: {clientId}")
    
    let jokeId = parseInt(jokeIdStr)
    let jokeOpt = getJokeById(jokeId)
    
    if jokeOpt.isNone():
      let errorResponse = %*{
        "error": "Joke not found",
        "message": fmt"No joke found with ID: {jokeId}"
      }
      resp Http404, errorResponse, "application/json"
    
    let bodyJson = parseJson(request.body)
    let voteType = bodyJson["vote"].getInt()
    
    if voteType notin [-1, 1]:
      let errorResponse = %*{
        "error": "Invalid vote",
        "message": "Vote must be 1 (upvote) or -1 (downvote)"
      }
      resp Http400, errorResponse, "application/json"
    
    let success = voteStore.addVote(jokeId, clientId, voteType)
    
    if success:
      let totalVotes = voteStore.getVoteCount(jokeId)
      let responseData = %*{
        "success": true,
        "jokeId": jokeId,
        "totalVotes": totalVotes,
        "userVote": voteType
      }
      resp Http200, responseData, "application/json"
    else:
      let errorResponse = %*{
        "error": "Vote failed",
        "message": "You have already voted this way"
      }
      resp Http400, errorResponse, "application/json"

  get "/categories":
    let clientId = getClientId(request)
    info(fmt"GET /categories - Client: {clientId}")
    
    if limiter.isRateLimited(clientId):
      warn(fmt"Rate limit exceeded for client: {clientId}")
      let errorResponse = %*{
        "error": "Rate limit exceeded",
        "message": fmt"Too many requests. Limit is {MAX_REQUESTS_PER_MINUTE} per minute."
      }
      addRateLimitHeaders(response, limiter, clientId)
      resp Http429, errorResponse, "application/json"
    
    var categories = initHashSet[string]()
    for joke in jokes:
      categories.incl(joke.category)
    
    let responseData = %*{
      "categories": toJson(categories.toSeq())
    }
    
    addRateLimitHeaders(response, limiter, clientId)
    resp Http200, responseData, "application/json"

  post "/jokes":
    let clientId = getClientId(request)
    info(fmt"POST /jokes - Client: {clientId}")
    
    if limiter.isRateLimited(clientId):
      warn(fmt"Rate limit exceeded for client: {clientId}")
      let errorResponse = %*{
        "error": "Rate limit exceeded",
        "message": fmt"Too many requests. Limit is {MAX_REQUESTS_PER_MINUTE} per minute."
      }
      addRateLimitHeaders(response, limiter, clientId)
      resp Http429, errorResponse, "application/json"
    
    let bodyJson = parseJson(request.body)
    
    let category = bodyJson["category"].getStr()
    let question = bodyJson["question"].getStr()
    let answer = bodyJson["answer"].getStr()
    
    if category == "" or question == "" or answer == "":
      let errorResponse = %*{
        "error": "Invalid submission",
        "message": "category, question, and answer are required"
      }
      resp Http400, errorResponse, "application/json"
    
    let submissionId = submissionStore.addSubmission(category, question, answer, clientId)
    
    let responseData = %*{
      "success": true,
      "submissionId": submissionId,
      "message": "Joke submitted for review"
    }
    
    addRateLimitHeaders(response, limiter, clientId)
    resp Http201, responseData, "application/json"

  get "/admin":
    info("GET /admin")
    resp Http200, generateAdminHtml(), "text/html"

  post "/admin/login":
    info("POST /admin/login")
    
    let bodyJson = parseJson(request.body)
    let username = bodyJson["username"].getStr()
    let password = bodyJson["password"].getStr()
    
    if adminStore.authenticate(username, password):
      let sessionId = adminStore.createSession(username)
      let responseData = %*{
        "success": true,
        "sessionId": sessionId,
        "username": username
      }
      resp Http200, responseData, "application/json"
    else:
      let errorResponse = %*{
        "error": "Authentication failed",
        "message": "Invalid username or password"
      }
      resp Http401, errorResponse, "application/json"

  post "/admin/logout":
    info("POST /admin/logout")
    let sessionId = getSessionId(request)
    adminStore.destroySession(sessionId)
    let responseData = %*{"success": true}
    resp Http200, responseData, "application/json"

  get "/admin/submissions/pending":
    let usernameOpt = requireAuth(request)
    if usernameOpt.isNone():
      let errorResponse = %*{"error": "Unauthorized"}
      resp Http401, errorResponse, "application/json"
    
    info(fmt"GET /admin/submissions/pending - Admin: {usernameOpt.get()}")
    
    let pending = submissionStore.getSubmissions(Pending)
    var subsArray = newJArray()
    for sub in pending:
      subsArray.add(sub.toJson())
    
    let responseData = %*{"submissions": subsArray}
    resp Http200, responseData, "application/json"

  get "/admin/submissions/approved":
    let usernameOpt = requireAuth(request)
    if usernameOpt.isNone():
      let errorResponse = %*{"error": "Unauthorized"}
      resp Http401, errorResponse, "application/json"
    
    info(fmt"GET /admin/submissions/approved - Admin: {usernameOpt.get()}")
    
    let approved = submissionStore.getSubmissions(Approved)
    var subsArray = newJArray()
    for sub in approved:
      subsArray.add(sub.toJson())
    
    let responseData = %*{"submissions": subsArray}
    resp Http200, responseData, "application/json"

  post "/admin/submissions/@id/approve":
    let usernameOpt = requireAuth(request)
    if usernameOpt.isNone():
      let errorResponse = %*{"error": "Unauthorized"}
      resp Http401, errorResponse, "application/json"
    
    let idStr = @"id"
    let id = parseInt(idStr)
    let username = usernameOpt.get()
    
    info(fmt"POST /admin/submissions/{id}/approve - Admin: {username}")
    
    let approved = submissionStore.approveSubmission(id, username)
    if approved.isSome():
      let sub = approved.get()
      
      let newJoke = Joke(
        id: nextJokeId,
        category: sub.category,
        question: sub.question,
        answer: sub.answer,
        votes: 0
      )
      jokes.add(newJoke)
      inc(nextJokeId)
      saveJokes()
      
      let responseData = %*{"success": true, "jokeId": newJoke.id}
      resp Http200, responseData, "application/json"
    else:
      let errorResponse = %*{"error": "Submission not found or already reviewed"}
      resp Http404, errorResponse, "application/json"

  post "/admin/submissions/@id/reject":
    let usernameOpt = requireAuth(request)
    if usernameOpt.isNone():
      let errorResponse = %*{"error": "Unauthorized"}
      resp Http401, errorResponse, "application/json"
    
    let idStr = @"id"
    let id = parseInt(idStr)
    let username = usernameOpt.get()
    
    info(fmt"POST /admin/submissions/{id}/reject - Admin: {username}")
    
    let rejected = submissionStore.rejectSubmission(id, username)
    if rejected.isSome():
      let responseData = %*{"success": true}
      resp Http200, responseData, "application/json"
    else:
      let errorResponse = %*{"error": "Submission not found or already reviewed"}
      resp Http404, errorResponse, "application/json"

  get "/admin/jokes/top":
    let usernameOpt = requireAuth(request)
    if usernameOpt.isNone():
      let errorResponse = %*{"error": "Unauthorized"}
      resp Http401, errorResponse, "application/json"
    
    info(fmt"GET /admin/jokes/top - Admin: {usernameOpt.get()}")
    
    let topJokes = voteStore.getTopJokes(50)
    
    var resultArray = newJArray()
    for (jokeId, score) in topJokes:
      let jokeOpt = getJokeById(jokeId)
      if jokeOpt.isSome():
        let joke = jokeOpt.get()
        resultArray.add(%*{
          "id": joke.id,
          "category": joke.category,
          "question": joke.question,
          "answer": joke.answer,
          "votes": score
        })
    
    let responseData = %*{"jokes": resultArray}
    resp Http200, responseData, "application/json"

when isMainModule:
  initLogger()
  initRandom()
  
  info("Starting Random Jokes API...")
  info(fmt"Loading jokes from {JOKES_FILE}...")
  
  try:
    jokes = loadJokes()
    nextJokeId = 1
    for joke in jokes:
      if joke.id >= nextJokeId:
        nextJokeId = joke.id + 1
    info(fmt"Loaded {jokes.len} jokes successfully, next ID: {nextJokeId}")
  except IOError as e:
    error(fmt"Failed to load jokes: {e.msg}")
    quit(1)
  
  limiter = newRateLimiter(MAX_REQUESTS_PER_MINUTE, TIME_WINDOW_SECONDS)
  info(fmt"Rate limiter configured: {MAX_REQUESTS_PER_MINUTE} requests per {TIME_WINDOW_SECONDS} seconds")
  
  submissionStore = newSubmissionStore(SUBMISSIONS_FILE)
  info(fmt"Submission store initialized: {SUBMISSIONS_FILE}")
  
  voteStore = newVoteStore(VOTES_FILE)
  info(fmt"Vote store initialized: {VOTES_FILE}")
  
  adminStore = newAdminStore(ADMIN_FILE)
  info(fmt"Admin store initialized: {ADMIN_FILE}")
  
  info("Server starting on port 5000...")
  runForever()