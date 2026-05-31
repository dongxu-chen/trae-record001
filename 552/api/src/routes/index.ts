import { Router } from 'express';
import { upload } from '../middleware/upload.middleware.js';
import {
  uploadAndVerify,
  getVerificationById,
  getAllVerifications,
  batchVerify,
  getBatchStatus,
} from '../controllers/verify.controller.js';
import {
  getHTMLReport,
  getPDFReport,
} from '../controllers/report.controller.js';
import {
  getTrustedCertificates,
} from '../controllers/certificate.controller.js';
import {
  getComplianceRules,
  getComplianceStandards,
} from '../controllers/compliance.controller.js';

const router = Router();

router.post('/verify', upload.single('file'), uploadAndVerify);
router.post('/verify/batch', upload.array('files', 20), batchVerify);
router.get('/verify/batch/:batchId', getBatchStatus);
router.get('/verify/:id', getVerificationById);
router.get('/verify', getAllVerifications);

router.get('/report/:id/html', getHTMLReport);
router.get('/report/:id/pdf', getPDFReport);

router.get('/certificates/trusted', getTrustedCertificates);

router.get('/compliance/rules', getComplianceRules);
router.get('/compliance/standards', getComplianceStandards);

export default router;
