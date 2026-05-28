export interface Point {
  x: number
  y: number
  p: number
  t: number
}
export type Stroke = Point[]

export interface Segment {
  strokes: Stroke[]
  bbox: { x: number; y: number; w: number; h: number }
}

export interface Candidate {
  char: string
  score: number
}

export interface UserTemplate {
  char: string
  pixels: Uint8Array
  norm: number
}

export type WorkerRequest =
  | { type: 'init' }
  | { type: 'recognize'; strokes: Stroke[]; topK: number }
  | { type: 'addUserTemplate'; char: string; pixels: Uint8Array; norm: number }
  | { type: 'removeUserTemplate'; char: string }
  | { type: 'clearUserTemplates' }

export type WorkerResponse =
  | { type: 'ready' }
  | { type: 'warmupProgress'; percent: number }
  | { type: 'recognized'; results: Candidate[][]; segments: Segment[] }
  | { type: 'error'; message: string }
  | { type: 'userTemplateAdded'; char: string }
