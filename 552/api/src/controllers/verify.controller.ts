import { type Request, type Response, type NextFunction, Router } from 'express';
import { nanoid } from 'nanoid';
import { VerificationService } from '../services/verification.service.js';
import type { VerifyOptions, VerificationRecord } from '../../../shared/index.js';

const router = Router();
const verificationService = new VerificationService();

export const uploadAndVerify = async (
  req: Request,
  res: Response,
  next: NextFunction,
): Promise<void> => {
  try {
    if (!req.file) {
      res.status(400).json({
        success: false,
        error: 'No file uploaded',
      });
      return;
    }

    const options: VerifyOptions = {
      verifyLevel: req.body.verifyLevel || 'standard',
      complianceStandard: req.body.complianceStandard || 'cn-es',
      checkRevocation: req.body.checkRevocation === 'true',
      checkTimestamp: req.body.checkTimestamp === 'true',
      customTrustCerts: req.body.customTrustCerts
        ? JSON.parse(req.body.customTrustCerts)
        : undefined,
    };

    const result = await verificationService.verify(
      new Uint8Array(req.file.buffer),
      req.file.originalname,
      options,
    );

    res.status(200).json({
      success: true,
      data: result,
    });
  } catch (error) {
    next(error);
  }
};

export const batchVerify = async (
  req: Request,
  res: Response,
  next: NextFunction,
): Promise<void> => {
  try {
    const files = req.files as Express.Multer.File[] | undefined;

    if (!files || files.length === 0) {
      res.status(400).json({
        success: false,
        error: 'No files uploaded for batch verification',
      });
      return;
    }

    if (files.length > 20) {
      res.status(400).json({
        success: false,
        error: 'Maximum 20 files per batch',
      });
      return;
    }

    const options: VerifyOptions = {
      verifyLevel: req.body.verifyLevel || 'standard',
      complianceStandard: req.body.complianceStandard || 'cn-es',
      checkRevocation: req.body.checkRevocation === 'true',
      checkTimestamp: req.body.checkTimestamp === 'true',
      customTrustCerts: req.body.customTrustCerts
        ? JSON.parse(req.body.customTrustCerts)
        : undefined,
    };

    const batchFiles = files.map((file) => ({
      id: nanoid(12),
      fileData: new Uint8Array(file.buffer),
      fileName: file.originalname,
    }));

    const result = await verificationService.batchVerify(batchFiles, options);

    res.status(200).json({
      success: true,
      data: result,
    });
  } catch (error) {
    next(error);
  }
};

export const getBatchStatus = (
  req: Request,
  res: Response,
  next: NextFunction,
): void => {
  try {
    const { batchId } = req.params;
    const status = verificationService.getBatchStatus(batchId);

    if (!status) {
      res.status(404).json({
        success: false,
        error: 'Batch job not found',
      });
      return;
    }

    res.status(200).json({
      success: true,
      data: status,
    });
  } catch (error) {
    next(error);
  }
};

export const getVerificationById = (
  req: Request,
  res: Response,
  next: NextFunction,
): void => {
  try {
    const { id } = req.params;
    const record = verificationService.getVerificationById(id);

    if (!record) {
      res.status(404).json({
        success: false,
        error: 'Verification record not found',
      });
      return;
    }

    res.status(200).json({
      success: true,
      data: record,
    });
  } catch (error) {
    next(error);
  }
};

export const getAllVerifications = (
  req: Request,
  res: Response,
  next: NextFunction,
): void => {
  try {
    const records: VerificationRecord[] = verificationService.getAllVerifications();
    res.status(200).json({
      success: true,
      data: records,
    });
  } catch (error) {
    next(error);
  }
};

export default router;
