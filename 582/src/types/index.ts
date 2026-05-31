export interface CardAttribute {
  attack: number;
  defense: number;
  health: number;
  cost: number;
}

export interface CardSkill {
  name: string;
  description: string;
  tags: string[];
  icon?: string;
}

export interface CardData {
  id: string;
  name: string;
  type: 'attack' | 'defense' | 'magic' | 'support';
  rarity: 'common' | 'rare' | 'epic' | 'legendary';
  element?: 'fire' | 'water' | 'earth' | 'wind' | 'light' | 'dark';
  attributes: CardAttribute;
  skills: CardSkill[];
  description: string;
  flavorText?: string;
  templateId: string;
  backgroundImage?: string;
  characterImage?: string;
  createdAt: string;
  updatedAt: string;
}

export interface TextLayout {
  x: number;
  y: number;
  fontSize: number;
  color: string;
  fontFamily?: string;
  fontWeight?: string | number;
  fontStyle?: string;
  textAnchor?: 'start' | 'middle' | 'end';
  prefix?: string;
}

export interface LoopItemLayout {
  type: 'loop';
  arrayPath: string;
  itemSpacing: number;
  startY: number;
  maxItems?: number;
  itemLayout: {
    title: TextLayout;
    description?: TextLayout;
    indent?: number;
  };
  headerLine?: boolean;
  separator?: boolean;
}

export interface BlockLayout {
  x: number;
  y: number;
  maxWidth: number;
  fontSize: number;
  lineHeight?: number;
  color?: string;
  fontFamily?: string;
  fontStyle?: string;
  prefix?: string;
}

export interface PositionSize {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface AttributeLayout extends TextLayout {
  icon?: string;
  circle?: boolean;
}

export interface TemplateLayout {
  name: TextLayout;
  type: TextLayout;
  rarity: { x: number; y: number; iconSize: number };
  attributes: {
    attack: AttributeLayout;
    defense: AttributeLayout;
    health: AttributeLayout;
    cost: AttributeLayout;
  };
  skills: BlockLayout | LoopItemLayout;
  description: BlockLayout;
  flavorText: BlockLayout;
  backgroundImage: PositionSize;
  characterImage: PositionSize;
}

export interface CardTemplate {
  id: string;
  name: string;
  description: string;
  style: 'fantasy' | 'sci-fi' | 'minimal' | 'classic' | 'custom';
  width: number;
  height: number;
  layout: TemplateLayout;
  colors: Record<string, string>;
  borders: {
    width: number;
    color: string;
    radius: number;
    style: 'solid' | 'ornate' | 'double';
  };
  builtIn: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface PrintLayoutOptions {
  paperSize: 'A4' | 'A3' | 'Letter';
  orientation: 'portrait' | 'landscape';
  columns: number;
  rows: number;
  margin: number;
  bleed: number;
  cropMarks: boolean;
  cardIds?: string[];
}

export interface AICardRequest {
  description: string;
  style?: 'fantasy' | 'sci-fi' | 'minimal' | 'classic';
  rarity?: 'common' | 'rare' | 'epic' | 'legendary';
  type?: 'attack' | 'defense' | 'magic' | 'support';
}

export interface BalanceAnalysis {
  score: number;
  grade: 'S' | 'A' | 'B' | 'C' | 'D' | 'F';
  issues: Array<{
    type: 'warning' | 'error' | 'info';
    category: string;
    message: string;
    suggestion?: string;
  }>;
  stats: {
    totalPower: number;
    costEfficiency: number;
    attributeDistribution: Record<string, number>;
    skillPower: number;
    rarityScore: number;
  };
  recommendations: string[];
}

export interface BattleCard extends CardData {
  currentHealth: number;
  buffs: Array<{ name: string; value: number; duration: number }>;
  debuffs: Array<{ name: string; value: number; duration: number }>;
}

export interface BattleResult {
  winner: 'player1' | 'player2' | 'draw';
  turns: number;
  log: string[];
  stats: {
    player1DamageDealt: number;
    player2DamageDealt: number;
    cardsPlayed: number;
    cardsDestroyed: number;
  };
  analysis: {
    deck1Strength: number;
    deck2Strength: number;
    keyMoments: string[];
  };
}

export interface DeckAnalysis {
  deckStrength: number;
  curve: Array<{ cost: number; count: number }>;
  typeDistribution: Record<string, number>;
  rarityDistribution: Record<string, number>;
  recommendations: string[];
  synergyScore: number;
}
