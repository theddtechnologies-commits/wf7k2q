// Mirrors backend/app/schemas.py — the API contract.

export interface Filters {
  start: string // ISO date, first UK delivery day
  end: string // ISO date, last UK delivery day
  cutoffTime: string // HH:MM, UK local time
  cutoffDaysBefore: number
  confidence: number // 0.5–0.99
}

export interface Meta {
  delivery_start: string
  delivery_end: string
  default_cutoff_time: string
  default_cutoff_days_before: number
  default_confidence: number
  cutoff_rationale: string
  actuals_rows: number
  forecast_rows: number
  forecast_publishes: number
}

export interface TimeseriesPoint {
  start_time: string
  actual_mw: number
  forecast_mw: number | null
  publish_time: string | null
  horizon_h: number | null
  error_mw: number | null
}

export interface TimeseriesResponse {
  points: TimeseriesPoint[]
}

export interface Summary {
  n: number
  coverage_pct: number
  mae_mw: number
  rmse_mw: number
  bias_mw: number
  nmae_pct_of_mean_actual: number
  nmae_pct_of_max_actual: number
  p10_error_mw: number
  p50_error_mw: number
  p90_error_mw: number
  p90_abs_error_mw: number
  mean_actual_mw: number
  max_actual_mw: number
}

export interface HourStats {
  hour: number
  n: number
  mae_mw: number
  bias_mw: number
  p10_error_mw: number
  p90_error_mw: number
  buffer_mw: number
}

export interface DayStats {
  date: string
  n: number
  mae_mw: number
  bias_mw: number
  mean_actual_mw: number
  mean_forecast_mw: number
}

export interface HistogramBin {
  bin_start_mw: number
  bin_end_mw: number
  count: number
}

export interface Recommendation {
  confidence: number
  buffer_mw: number
  buffer_pct_of_mean_forecast: number
  shortfall_hours_pct: number
  riskiest_hours: number[]
  headline: string
}

export interface MetricsResponse {
  summary: Summary
  by_hour: HourStats[]
  by_day: DayStats[]
  histogram: HistogramBin[]
  recommendation: Recommendation
}

export interface HorizonBucket {
  horizon_start_h: number
  horizon_end_h: number
  n: number
  mae_mw: number
  rmse_mw: number
  bias_mw: number
  p90_abs_error_mw: number
}

export interface HorizonResponse {
  bucket_hours: number
  buckets: HorizonBucket[]
}
