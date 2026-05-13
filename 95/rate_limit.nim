import times, tables, options, hashes, locks, strutils

type
  RateLimiter* = object
    maxRequests*: int
    timeWindowSeconds*: int
    requests: Table[string, seq[Time]]
    lock: Lock
    trustedProxies: HashSet[string]

proc newRateLimiter*(maxRequests: int, timeWindowSeconds: int): RateLimiter =
  result = RateLimiter(
    maxRequests: maxRequests,
    timeWindowSeconds: timeWindowSeconds,
    requests: initTable[string, seq[Time]](),
    lock: initLock(result.lock),
    trustedProxies: initHashSet[string]()
  )
  result.trustedProxies.incl("127.0.0.1")
  result.trustedProxies.incl("::1")

proc addTrustedProxy*(limiter: var RateLimiter, proxyIp: string) =
  withLock limiter.lock:
    limiter.trustedProxies.incl(proxyIp)

proc extractRealClientId*(limiter: var RateLimiter, xForwardedFor: string, directClientIp: string, userAgent: string = ""): string =
  withLock limiter.lock:
    if xForwardedFor == "":
      result = directClientIp
    else:
      let ips = xForwardedFor.split(",").map(s => s.strip())
      var realIp = directClientIp
      
      for ip in reversed(ips):
        if limiter.trustedProxies.contains(ip):
          continue
        realIp = ip
        break
      
      if realIp == directClientIp and ips.len > 0:
        realIp = ips[0]
      
      result = realIp
    
    if userAgent != "":
      result = result & "|" & $hash(userAgent)

proc isRateLimited*(limiter: var RateLimiter, clientId: string): bool =
  let now = getTime()
  let windowStart = now - initDuration(seconds = limiter.timeWindowSeconds)
  
  withLock limiter.lock:
    if not limiter.requests.hasKey(clientId):
      limiter.requests[clientId] = @[]
    
    var recentRequests = limiter.requests[clientId]
    recentRequests = recentRequests.filter(t => t >= windowStart)
    limiter.requests[clientId] = recentRequests
    
    if recentRequests.len >= limiter.maxRequests:
      return true
    
    recentRequests.add(now)
    limiter.requests[clientId] = recentRequests
    return false

proc getRemaining*(limiter: RateLimiter, clientId: string): int =
  if not limiter.requests.hasKey(clientId):
    return limiter.maxRequests
  return max(0, limiter.maxRequests - limiter.requests[clientId].len)

proc getResetTime*(limiter: RateLimiter, clientId: string): Option[int] =
  if not limiter.requests.hasKey(clientId) or limiter.requests[clientId].len == 0:
    return none(int)
  
  let requests = limiter.requests[clientId]
  let earliest = requests.sorted()[0]
  let resetTime = earliest + initDuration(seconds = limiter.timeWindowSeconds)
  let now = getTime()
  
  let secondsRemaining = int((resetTime - now).inSeconds)
  if secondsRemaining > 0:
    return some(secondsRemaining)
  else:
    return none(int)