import { type Request, type Response, type NextFunction, Router } from 'express';
import { ReportService } from '../services/report.service.js';
import { VerificationService } from '../services/verification.service.js';

const router = Router();
const reportService = new ReportService();
const verificationService = new VerificationService();

export const getHTMLReport = (
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

    const verifyResponse = {
      id: record.id,
      status: record.status as 'pending' | 'processing' | 'completed' | 'failed',
      overallResult: record.overallResult as 'valid' | 'invalid' | 'warning' | 'error',
      score: record.score,
      fileInfo: {
        name: record.fileName,
        size: 0,
        type: '',
        hash: record.fileHash,
      },
      signatureFormat: record.signatureFormat as 'PAdES' | 'XAdES' | 'CAdES' | 'unknown',
      timestamp: new Date(record.createdAt).getTime(),
      results: record.results,
    };

    const html = reportService.generateHTMLReport(verifyResponse);

    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    res.setHeader('Content-Disposition', `inline; filename="verification-report-${id}.html"`);
    res.status(200).send(html);
  } catch (error) {
    next(error);
  }
};

export const getPDFReport = async (
  req: Request,
  res: Response,
  next: NextFunction,
): Promise<void> => {
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

    const verifyResponse = {
      id: record.id,
      status: record.status as 'pending' | 'processing' | 'completed' | 'failed',
      overallResult: record.overallResult as 'valid' | 'invalid' | 'warning' | 'error',
      score: record.score,
      fileInfo: {
        name: record.fileName,
        size: 0,
        type: '',
        hash: record.fileHash,
      },
      signatureFormat: record.signatureFormat as 'PAdES' | 'XAdES' | 'CAdES' | 'unknown',
      timestamp: new Date(record.createdAt).getTime(),
      results: record.results,
    };

    const pdfBuffer = await reportService.generatePDFReport(verifyResponse);

    res.setHeader('Content-Type', 'application/pdf');
    res.setHeader('Content-Disposition', `attachment; filename="verification-report-${id}.pdf"`);
    res.status(200).send(Buffer.from(pdfBuffer));
  } catch (error) {
    next(error);
  }
};

export default router;
