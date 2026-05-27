import { type Request, type Response } from 'express';
import { getAddressNFTs, getCollectionInfo } from '../services/nft.js';

export async function getAddressNFTsHandler(req: Request, res: Response): Promise<void> {
  try {
    const address = req.params.address;
    const nfts = await getAddressNFTs(address);
    res.json({ success: true, data: nfts });
  } catch (error) {
    res.status(500).json({ success: false, error: (error as Error).message });
  }
}

export async function getCollectionInfoHandler(req: Request, res: Response): Promise<void> {
  try {
    const contractAddress = req.params.contractAddress;
    const info = await getCollectionInfo(contractAddress);
    if (!info) {
      res.status(404).json({ success: false, error: 'Collection not found' });
      return;
    }
    res.json({ success: true, data: info });
  } catch (error) {
    res.status(500).json({ success: false, error: (error as Error).message });
  }
}
