import json, times, locks, os, strutils

type
  SubmissionStatus* = enum
    Pending,
    Approved,
    Rejected
  
  Submission* = object
    id*: int
    category*: string
    question*: string
    answer*: string
    submittedBy*: string
    submittedAt*: Time
    status*: SubmissionStatus
    reviewedAt*: Option[Time]
    reviewedBy*: Option[string]
  
  SubmissionStore* = object
    submissions*: seq[Submission]
    nextId*: int
    filePath*: string
    lock*: Lock

proc newSubmissionStore*(filePath: string): SubmissionStore =
  result = SubmissionStore(
    submissions: @[],
    nextId: 1,
    filePath: filePath,
    lock: initLock(result.lock)
  )
  if fileExists(filePath):
    result.loadFromFile()

proc saveToFile*(store: var SubmissionStore) =
  withLock store.lock:
    var jsonArray = newJArray()
    for sub in store.submissions:
      let statusStr = case sub.status
        of Pending: "pending"
        of Approved: "approved"
        of Rejected: "rejected"
      
      let node = %*{
        "id": sub.id,
        "category": sub.category,
        "question": sub.question,
        "answer": sub.answer,
        "submittedBy": sub.submittedBy,
        "submittedAt": sub.submittedAt.format("yyyy-MM-dd HH:mm:ss"),
        "status": statusStr
      }
      
      if sub.reviewedAt.isSome():
        node["reviewedAt"] = %sub.reviewedAt.get().format("yyyy-MM-dd HH:mm:ss")
      if sub.reviewedBy.isSome():
        node["reviewedBy"] = %sub.reviewedBy.get()
      
      jsonArray.add(node)
    
    let jsonContent = %*{"submissions": jsonArray}
    writeFile(store.filePath, $jsonContent)

proc loadFromFile*(store: var SubmissionStore) =
  withLock store.lock:
    if not fileExists(store.filePath):
      return
    
    let content = readFile(store.filePath)
    let jsonData = parseJson(content)
    let subsArray = jsonData["submissions"]
    
    for subNode in subsArray:
      let status = case subNode["status"].getStr()
        of "pending": Pending
        of "approved": Approved
        of "rejected": Rejected
        else: Pending
      
      var reviewedAt = none(Time)
      if subNode.hasKey("reviewedAt"):
        let tsStr = subNode["reviewedAt"].getStr()
        reviewedAt = some(parse(tsStr, "yyyy-MM-dd HH:mm:ss"))
      
      var reviewedBy = none(string)
      if subNode.hasKey("reviewedBy"):
        reviewedBy = some(subNode["reviewedBy"].getStr())
      
      let sub = Submission(
        id: subNode["id"].getInt(),
        category: subNode["category"].getStr(),
        question: subNode["question"].getStr(),
        answer: subNode["answer"].getStr(),
        submittedBy: subNode["submittedBy"].getStr(),
        submittedAt: parse(subNode["submittedAt"].getStr(), "yyyy-MM-dd HH:mm:ss"),
        status: status,
        reviewedAt: reviewedAt,
        reviewedBy: reviewedBy
      )
      
      store.submissions.add(sub)
      if sub.id >= store.nextId:
        store.nextId = sub.id + 1

proc addSubmission*(store: var SubmissionStore, category, question, answer, submittedBy: string): int =
  withLock store.lock:
    let submission = Submission(
      id: store.nextId,
      category: category,
      question: question,
      answer: answer,
      submittedBy: submittedBy,
      submittedAt: getTime(),
      status: Pending,
      reviewedAt: none(Time),
      reviewedBy: none(string)
    )
    store.submissions.add(submission)
    inc(store.nextId)
    store.saveToFile()
    return submission.id

proc getSubmissions*(store: SubmissionStore, status: SubmissionStatus = Pending): seq[Submission] =
  withLock store.lock:
    return store.submissions.filter(s => s.status == status)

proc getSubmissionById*(store: SubmissionStore, id: int): Option[Submission] =
  withLock store.lock:
    for sub in store.submissions:
      if sub.id == id:
        return some(sub)
    return none(Submission)

proc approveSubmission*(store: var SubmissionStore, id: int, reviewedBy: string): Option[Submission] =
  withLock store.lock:
    for i in 0..<store.submissions.len:
      if store.submissions[i].id == id and store.submissions[i].status == Pending:
        store.submissions[i].status = Approved
        store.submissions[i].reviewedAt = some(getTime())
        store.submissions[i].reviewedBy = some(reviewedBy)
        store.saveToFile()
        return some(store.submissions[i])
    return none(Submission)

proc rejectSubmission*(store: var SubmissionStore, id: int, reviewedBy: string): Option[Submission] =
  withLock store.lock:
    for i in 0..<store.submissions.len:
      if store.submissions[i].id == id and store.submissions[i].status == Pending:
        store.submissions[i].status = Rejected
        store.submissions[i].reviewedAt = some(getTime())
        store.submissions[i].reviewedBy = some(reviewedBy)
        store.saveToFile()
        return some(store.submissions[i])
    return none(Submission)

proc toJson*(submission: Submission): JsonNode =
  let statusStr = case submission.status
    of Pending: "pending"
    of Approved: "approved"
    of Rejected: "rejected"
  
  result = %*{
    "id": submission.id,
    "category": submission.category,
    "question": submission.question,
    "answer": submission.answer,
    "submittedBy": submission.submittedBy,
    "submittedAt": submission.submittedAt.format("yyyy-MM-dd HH:mm:ss"),
    "status": statusStr
  }
  
  if submission.reviewedAt.isSome():
    result["reviewedAt"] = %submission.reviewedAt.get().format("yyyy-MM-dd HH:mm:ss")
  if submission.reviewedBy.isSome():
    result["reviewedBy"] = %submission.reviewedBy.get()