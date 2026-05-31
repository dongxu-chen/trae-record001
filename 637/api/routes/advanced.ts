import { Router } from 'express';
import {
  getTeamConfig,
  updateTeamConfig,
  resetConfig,
  addRule,
  updateRule,
  deleteRule,
  validateNameAgainstRules,
  addForbiddenWordHandler,
  removeForbiddenWordHandler,
  syncConfig,
  exportConfig,
  importConfig,
  getPresetRules,
  batchRename,
  detectVariables,
  generateDiffHandler,
  validateRenameHandler,
  detectConflictsHandler,
  detectAllConflictsHandler,
  validateNameHandler,
  checkScopeConflictsHandler
} from '../controllers/advancedController.js';

const router = Router();

router.get('/team/config', getTeamConfig);
router.put('/team/config', updateTeamConfig);
router.post('/team/config/reset', resetConfig);
router.post('/team/config/sync', syncConfig);
router.get('/team/config/export', exportConfig);
router.post('/team/config/import', importConfig);

router.post('/team/rules', addRule);
router.put('/team/rules/:id', updateRule);
router.delete('/team/rules/:id', deleteRule);
router.post('/team/rules/validate', validateNameAgainstRules);

router.post('/team/forbidden-words', addForbiddenWordHandler);
router.delete('/team/forbidden-words/:word', removeForbiddenWordHandler);

router.get('/team/presets/:preset', getPresetRules);

router.post('/batch/rename', batchRename);
router.post('/batch/detect-variables', detectVariables);
router.post('/batch/diff', generateDiffHandler);
router.post('/batch/validate', validateRenameHandler);

router.post('/conflicts/detect', detectConflictsHandler);
router.post('/conflicts/detect-all', detectAllConflictsHandler);
router.post('/conflicts/validate-name', validateNameHandler);
router.post('/conflicts/check-scope', checkScopeConflictsHandler);

export default router;
