import { type Request, type Response, type NextFunction, Router } from 'express';
import { ComplianceService } from '../services/compliance.service.js';
import type { ComplianceStandard } from '../services/compliance.service.js';

const router = Router();
const complianceService = new ComplianceService();

export const getComplianceRules = (
  req: Request,
  res: Response,
  next: NextFunction,
): void => {
  try {
    const standard = (req.query.standard as ComplianceStandard) || 'cn-es';
    const rules = complianceService.getStandardRules(standard);

    if (!rules) {
      res.status(404).json({
        success: false,
        error: 'Compliance standard not found',
      });
      return;
    }

    res.status(200).json({
      success: true,
      data: rules,
    });
  } catch (error) {
    next(error);
  }
};

export const getComplianceStandards = (
  req: Request,
  res: Response,
  next: NextFunction,
): void => {
  try {
    const standards = complianceService.getSupportedStandards();
    res.status(200).json({
      success: true,
      data: standards,
    });
  } catch (error) {
    next(error);
  }
};

export default router;
