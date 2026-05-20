use std::f64::consts::SQRT_2;

#[derive(Debug, Clone, Default)]
pub struct PQLXMetrics {
    pub mean: f64,
    pub std_dev: f64,
    pub min: i32,
    pub max: i32,
    pub peak_to_peak: i32,
    pub rms: f64,
    pub skewness: f64,
    pub kurtosis: f64,
    pub num_samples: usize,
    pub num_gaps: usize,
    pub gap_percentage: f64,
    pub dc_offset: f64,
    pub cross_correlation: Option<f64>,
}

pub struct PQLXAnalyzer;

impl PQLXAnalyzer {
    pub fn analyze(samples: &[i32], gap_threshold: i32) -> PQLXMetrics {
        let n = samples.len();
        if n == 0 {
            return PQLXMetrics::default();
        }

        let sum: i64 = samples.iter().map(|&x| x as i64).sum();
        let mean = sum as f64 / n as f64;

        let sum_sq: f64 = samples.iter()
            .map(|&x| (x as f64 - mean).powi(2))
            .sum();
        let std_dev = (sum_sq / n as f64).sqrt();

        let min = *samples.iter().min().unwrap_or(&0);
        let max = *samples.iter().max().unwrap_or(&0);
        let peak_to_peak = max - min;

        let sum_sq_abs: f64 = samples.iter()
            .map(|&x| (x as f64).powi(2))
            .sum();
        let rms = (sum_sq_abs / n as f64).sqrt();

        let skewness = if std_dev > 1e-10 {
            let sum_cubed: f64 = samples.iter()
                .map(|&x| ((x as f64 - mean) / std_dev).powi(3))
                .sum();
            sum_cubed / n as f64
        } else {
            0.0
        };

        let kurtosis = if std_dev > 1e-10 {
            let sum_fourth: f64 = samples.iter()
                .map(|&x| ((x as f64 - mean) / std_dev).powi(4))
                .sum();
            (sum_fourth / n as f64) - 3.0
        } else {
            0.0
        };

        let mut num_gaps = 0;
        for window in samples.windows(2) {
            if (window[1] - window[0]).abs() > gap_threshold {
                num_gaps += 1;
            }
        }
        let gap_percentage = num_gaps as f64 / (n - 1).max(1) as f64 * 100.0;

        let dc_offset = mean.abs();

        PQLXMetrics {
            mean,
            std_dev,
            min,
            max,
            peak_to_peak,
            rms,
            skewness,
            kurtosis,
            num_samples: n,
            num_gaps,
            gap_percentage,
            dc_offset,
            cross_correlation: None,
        }
    }

    pub fn cross_correlate(a: &[i32], b: &[i32]) -> f64 {
        let n = a.len().min(b.len());
        if n == 0 {
            return 0.0;
        }

        let mean_a: f64 = a[..n].iter().map(|&x| x as f64).sum::<f64>() / n as f64;
        let mean_b: f64 = b[..n].iter().map(|&x| x as f64).sum::<f64>() / n as f64;

        let mut cov = 0.0;
        let mut var_a = 0.0;
        let mut var_b = 0.0;

        for i in 0..n {
            let da = a[i] as f64 - mean_a;
            let db = b[i] as f64 - mean_b;
            cov += da * db;
            var_a += da * da;
            var_b += db * db;
        }

        if var_a > 1e-10 && var_b > 1e-10 {
            cov / (var_a.sqrt() * var_b.sqrt())
        } else {
            0.0
        }
    }

    pub fn snr_estimate(samples: &[i32], noise_window: usize) -> f64 {
        let n = samples.len();
        if n < noise_window * 2 {
            return 0.0;
        }

        let noise_rms: f64 = samples[..noise_window].iter()
            .map(|&x| (x as f64).powi(2))
            .sum::<f64>().sqrt() / noise_window as f64;

        let signal_rms: f64 = samples[noise_window..noise_window * 2].iter()
            .map(|&x| (x as f64).powi(2))
            .sum::<f64>().sqrt() / noise_window as f64;

        if noise_rms > 1e-10 {
            20.0 * (signal_rms / noise_rms).log10()
        } else {
            0.0
        }
    }

    pub fn quality_score(metrics: &PQLXMetrics) -> f64 {
        let mut score = 100.0;

        if metrics.gap_percentage > 5.0 {
            score -= 20.0 * metrics.gap_percentage / 5.0;
        }

        if metrics.dc_offset > 1000.0 {
            score -= 15.0;
        }

        if metrics.std_dev < 1.0 {
            score -= 10.0;
        }

        if metrics.kurtosis.abs() > 10.0 {
            score -= 10.0;
        }

        score.clamp(0.0, 100.0)
    }
}

#[derive(Debug, Clone)]
pub struct MultiChannelMetrics {
    pub channel_metrics: std::collections::HashMap<String, PQLXMetrics>,
    pub overall_quality_score: f64,
}

impl MultiChannelMetrics {
    pub fn new() -> Self {
        Self {
            channel_metrics: std::collections::HashMap::new(),
            overall_quality_score: 0.0,
        }
    }

    pub fn add_channel(&mut self, name: String, metrics: PQLXMetrics) {
        self.channel_metrics.insert(name, metrics);
        self.update_overall_score();
    }

    fn update_overall_score(&mut self) {
        if self.channel_metrics.is_empty() {
            self.overall_quality_score = 0.0;
            return;
        }

        let total: f64 = self.channel_metrics.values()
            .map(|m| PQLXAnalyzer::quality_score(m))
            .sum();

        self.overall_quality_score = total / self.channel_metrics.len() as f64;
    }
}

impl Default for MultiChannelMetrics {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_analyze() {
        let samples: Vec<i32> = (0..100).map(|x| x).collect();
        let metrics = PQLXAnalyzer::analyze(&samples, 1000);
        assert_eq!(metrics.num_samples, 100);
        assert!(metrics.mean > 0.0);
    }

    #[test]
    fn test_cross_correlate() {
        let a: Vec<i32> = vec![1, 2, 3, 4, 5];
        let b: Vec<i32> = vec![1, 2, 3, 4, 5];
        let corr = PQLXAnalyzer::cross_correlate(&a, &b);
        assert!((corr - 1.0).abs() < 1e-6);
    }
}
