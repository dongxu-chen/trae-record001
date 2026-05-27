import { Router } from 'express';
import { getLatestBlocksHandler, getBlockHandler } from '../controllers/block.js';
import {
  getLatestTransactionsHandler,
  getTransactionHandler,
  getBlockTransactionsHandler,
} from '../controllers/transaction.js';
import {
  getAddressHandler,
  getAddressTransactionsHandler,
  getAddressTokensHandler,
} from '../controllers/address.js';
import { getLatestGasHandler, getGasHistoryHandler } from '../controllers/gas.js';
import {
  getContractHandler,
  verifyContractHandler,
  callContractHandler,
  readContractHandler,
  getContractEventsHandler,
  estimateGasHandler,
} from '../controllers/contract.js';
import { searchHandler } from '../controllers/search.js';
import { getAddressNFTsHandler, getCollectionInfoHandler } from '../controllers/nft.js';
import {
  getChainsHandler,
  getMultiChainAddressHandler,
  getChainBlockHandler,
} from '../controllers/multichain.js';

const router = Router();

router.get('/blocks/latest', getLatestBlocksHandler);
router.get('/blocks/:number', getBlockHandler);

router.get('/transactions/latest', getLatestTransactionsHandler);
router.get('/transactions/:hash', getTransactionHandler);
router.get('/blocks/:blockNumber/transactions', getBlockTransactionsHandler);

router.get('/address/:address', getAddressHandler);
router.get('/address/:address/transactions', getAddressTransactionsHandler);
router.get('/address/:address/tokens', getAddressTokensHandler);

router.get('/gas/latest', getLatestGasHandler);
router.get('/gas/history', getGasHistoryHandler);

router.get('/contract/:address', getContractHandler);
router.post('/contract/verify', verifyContractHandler);
router.post('/contract/:address/call', callContractHandler);
router.post('/contract/:address/read', readContractHandler);
router.post('/contract/:address/events', getContractEventsHandler);
router.post('/contract/:address/estimate-gas', estimateGasHandler);

router.get('/search', searchHandler);

router.get('/nft/address/:address', getAddressNFTsHandler);
router.get('/nft/collection/:contractAddress', getCollectionInfoHandler);

router.get('/chains', getChainsHandler);
router.get('/multichain/address/:address', getMultiChainAddressHandler);
router.get('/multichain/:chainId/block/:blockNumber', getChainBlockHandler);

export default router;
