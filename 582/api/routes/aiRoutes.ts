
import { Router, type Request, type Response } from 'express';
import * as aiCardService from '../services/aiCardService.js';
import * as battleService from '../services/battleService.js';
import * as cardService from '../services/cardService.js';
import type { AICardRequest } from '../types/index.js';

const router = Router();

router.post('/generate', async (req: Request, res: Response): Promise<void> => {
  try {
    const { description, style, rarity, type } = req.body as AICardRequest;
    if (!description) {
      res.status(400).json({ success: false, error: '描述不能为空' });
      return;
    }

    const cardData = aiCardService.generateAICard({ description, style, rarity, type });
    res.json({ success: true, data: cardData });
  } catch (error) {
    console.error('AI generate error:', error);
    res.status(500).json({ success: false, error: 'AI生成卡牌失败' });
  }
});

router.post('/balance/:id', async (req: Request, res: Response): Promise<void> => {
  try {
    const card = await cardService.getCard(req.params.id);
    if (!card) {
      res.status(404).json({ success: false, error: '卡牌不存在' });
      return;
    }

    const analysis = aiCardService.analyzeCardBalance(card);
    res.json({ success: true, data: analysis });
  } catch (error) {
    console.error('Balance analysis error:', error);
    res.status(500).json({ success: false, error: '平衡分析失败' });
  }
});

router.post('/balance', async (req: Request, res: Response): Promise<void> => {
  try {
    const cardData = req.body;
    if (!cardData.name || !cardData.attributes) {
      res.status(400).json({ success: false, error: '无效的卡牌数据' });
      return;
    }

    const analysis = aiCardService.analyzeCardBalance(cardData);
    res.json({ success: true, data: analysis });
  } catch (error) {
    console.error('Balance analysis error:', error);
    res.status(500).json({ success: false, error: '平衡分析失败' });
  }
});

router.post('/battle', async (req: Request, res: Response): Promise<void> => {
  try {
    const { deck1Ids, deck2Ids, deck1, deck2, maxTurns } = req.body;
    
    let deck1Cards: any[] = [];
    let deck2Cards: any[] = [];

    if (Array.isArray(deck1) && deck1.length > 0) {
      deck1Cards = deck1;
    } else if (Array.isArray(deck1Ids) && deck1Ids.length > 0) {
      for (const id of deck1Ids) {
        const card = await cardService.getCard(id);
        if (card) deck1Cards.push(card);
      }
    }

    if (Array.isArray(deck2) && deck2.length > 0) {
      deck2Cards = deck2;
    } else if (Array.isArray(deck2Ids) && deck2Ids.length > 0) {
      for (const id of deck2Ids) {
        const card = await cardService.getCard(id);
        if (card) deck2Cards.push(card);
      }
    }

    if (deck1Cards.length === 0 || deck2Cards.length === 0) {
      res.status(400).json({ success: false, error: '卡组不能为空或找不到有效的卡牌' });
      return;
    }

    const result = battleService.simulateBattle(deck1Cards, deck2Cards, maxTurns || 30);
    res.json({ success: true, data: result });
  } catch (error) {
    console.error('Battle simulation error:', error);
    res.status(500).json({ success: false, error: '对战模拟失败' });
  }
});

router.post('/deck/analyze', async (req: Request, res: Response): Promise<void> => {
  try {
    const { cardIds, cards: cardsParam } = req.body;
    
    let cards: any[] = [];

    if (Array.isArray(cardsParam) && cardsParam.length > 0) {
      cards = cardsParam;
    } else if (Array.isArray(cardIds) && cardIds.length > 0) {
      for (const id of cardIds) {
        const card = await cardService.getCard(id);
        if (card) cards.push(card);
      }
    } else {
      res.status(400).json({ success: false, error: '需要提供卡牌ID列表或卡牌数据' });
      return;
    }

    const analysis = battleService.analyzeDeck(cards);
    res.json({ success: true, data: analysis });
  } catch (error) {
    console.error('Deck analysis error:', error);
    res.status(500).json({ success: false, error: '卡组分析失败' });
  }
});

export default router;
