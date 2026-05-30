import React, { createContext, useContext, useState, useCallback } from 'react'

const CaptchaContext = createContext(null)

export const useCaptcha = () => {
  const context = useContext(CaptchaContext)
  if (!context) {
    throw new Error('useCaptcha must be used within a CaptchaProvider')
  }
  return context
}

export const CaptchaProvider = ({ children }) => {
  const [verifiedCaptchas, setVerifiedCaptchas] = useState(new Set())
  const [globalErrorCount, setGlobalErrorCount] = useState(0)
  const [isLocked, setIsLocked] = useState(false)
  const [lockUntil, setLockUntil] = useState(null)

  const MAX_ERRORS = 10
  const LOCK_DURATION = 60000

  const handleVerifySuccess = useCallback((captchaId) => {
    setVerifiedCaptchas(prev => new Set([...prev, captchaId]))
    setGlobalErrorCount(0)
  }, [])

  const handleVerifyError = useCallback((errorData) => {
    if (errorData?.locked) {
      setIsLocked(true)
      setLockUntil(Date.now() + LOCK_DURATION)
      setTimeout(() => {
        setIsLocked(false)
        setLockUntil(null)
        setGlobalErrorCount(0)
      }, LOCK_DURATION)
    } else {
      setGlobalErrorCount(prev => {
        const newCount = prev + 1
        if (newCount >= MAX_ERRORS) {
          setIsLocked(true)
          setLockUntil(Date.now() + LOCK_DURATION)
          setTimeout(() => {
            setIsLocked(false)
            setLockUntil(null)
            setGlobalErrorCount(0)
          }, LOCK_DURATION)
        }
        return newCount
      })
    }
  }, [])

  const isVerified = useCallback((captchaId) => {
    return verifiedCaptchas.has(captchaId)
  }, [verifiedCaptchas])

  const clearVerified = useCallback(() => {
    setVerifiedCaptchas(new Set())
  }, [])

  const getRemainingLockTime = useCallback(() => {
    if (!lockUntil) return 0
    return Math.max(0, Math.ceil((lockUntil - Date.now()) / 1000))
  }, [lockUntil])

  const value = {
    verifiedCaptchas,
    globalErrorCount,
    isLocked,
    lockUntil,
    handleVerifySuccess,
    handleVerifyError,
    isVerified,
    clearVerified,
    getRemainingLockTime,
    maxErrors: MAX_ERRORS,
  }

  return (
    <CaptchaContext.Provider value={value}>
      {children}
    </CaptchaContext.Provider>
  )
}

export default CaptchaContext
