import { Router } from 'express'
import { validateExpression, computeDerivative, evaluateExpression } from '../controllers/functionController.js'

const router = Router()

router.post('/validate', validateExpression)
router.post('/derivative', computeDerivative)
router.post('/evaluate', evaluateExpression)

export default router
