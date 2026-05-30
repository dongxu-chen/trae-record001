import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

export const captchaApi = {
  generateSlideCaptcha: (difficulty) => {
    const params = difficulty ? { difficulty } : {}
    return api.get('/captcha/slide', { params })
  },

  verifySlideCaptcha: (captchaId, x, y, trajectory, attempts, duration) => {
    return api.post('/captcha/slide/verify', { captchaId, x, y, trajectory, attempts, duration })
  },

  generateRotateCaptcha: (difficulty) => {
    const params = difficulty ? { difficulty } : {}
    return api.get('/captcha/rotate', { params })
  },

  verifyRotateCaptcha: (captchaId, angle, trajectory, attempts, duration) => {
    return api.post('/captcha/rotate/verify', { captchaId, angle, trajectory, attempts, duration })
  },

  generateClickCaptcha: (difficulty) => {
    const params = difficulty ? { difficulty } : {}
    return api.get('/captcha/click', { params })
  },

  verifyClickCaptcha: (captchaId, points, clickPattern, attempts, duration) => {
    return api.post('/captcha/click/verify', { captchaId, points, clickPattern, attempts, duration })
  },

  generateVoiceCaptcha: (difficulty) => {
    const params = difficulty ? { difficulty } : {}
    return api.get('/captcha/voice', { params })
  },

  getVoiceCaptcha: (captchaId) => {
    return api.get(`/captcha/voice/${captchaId}`, {
      responseType: 'blob',
    })
  },

  verifyVoiceCaptcha: (captchaId, code, attempts, duration) => {
    return api.post('/captcha/voice/verify', { captchaId, code, attempts, duration })
  },

  getCaptchaStats: (type) => {
    const params = type ? { type } : {}
    return api.get('/captcha/stats', { params })
  },

  getBehaviorAnalysis: (type) => {
    const params = type ? { type } : {}
    return api.get('/captcha/behavior-analysis', { params })
  },
}

export default api
