import type { Stock, StockPerformance } from './core'
import type { StockSignal, MentionWithTime } from './signal'

export interface StockRow extends Stock {
  signal: StockSignal
  mentions: MentionWithTime[]
  performance: StockPerformance | null
  recent: number[] // 近約 30 天日收盤（舊→新），給迷你走勢圖用
}
