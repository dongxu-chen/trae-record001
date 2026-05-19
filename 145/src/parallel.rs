use crate::pqlx::{PQLXAnalyzer, PQLXMetrics};
use crate::steim2::{Steim2Decoder, Steim2Error};
use rayon::prelude::*;
use std::collections::HashMap;

pub struct ParallelProcessor {
    num_threads: Option<usize>,
}

impl ParallelProcessor {
    pub fn new(num_threads: Option<usize>) -> Self {
        if let Some(n) = num_threads {
            rayon::ThreadPoolBuilder::new()
                .num_threads(n)
                .build_global()
                .ok();
        }
        Self { num_threads }
    }

    pub fn decode_many_stations(
        &self,
        station_data: &HashMap<String, Vec<u8>>,
    ) -> HashMap<String, Result<Vec<i32>, String>> {
        station_data
            .par_iter()
            .map(|(station_id, data)| {
                let mut decoder = Steim2Decoder::new();
                let aligned_data = Steim2Decoder::validate_alignment(data);
                
                let result = match decoder.add_frames(&aligned_data) {
                    Ok(_) => Ok(decoder.decode_all()),
                    Err(e) => Err(format!("Decode error for {}: {:?}", station_id, e)),
                };
                
                (station_id.clone(), result)
            })
            .collect()
    }

    pub fn analyze_many_stations(
        &self,
        station_samples: &HashMap<String, Vec<i32>>,
        gap_threshold: i32,
    ) -> HashMap<String, PQLXMetrics> {
        station_samples
            .par_iter()
            .map(|(station_id, samples)| {
                let metrics = PQLXAnalyzer::analyze(samples, gap_threshold);
                (station_id.clone(), metrics)
            })
            .collect()
    }

    pub fn decode_and_analyze(
        &self,
        station_data: &HashMap<String, Vec<u8>>,
        gap_threshold: i32,
    ) -> HashMap<String, (Result<Vec<i32>, String>, Option<PQLXMetrics>)> {
        station_data
            .par_iter()
            .map(|(station_id, data)| {
                let mut decoder = Steim2Decoder::new();
                let aligned_data = Steim2Decoder::validate_alignment(data);
                
                let decode_result = match decoder.add_frames(&aligned_data) {
                    Ok(_) => {
                        let samples = decoder.decode_all();
                        let metrics = PQLXAnalyzer::analyze(&samples, gap_threshold);
                        (Ok(samples), Some(metrics))
                    }
                    Err(e) => (Err(format!("Decode error: {:?}", e)), None),
                };
                
                (station_id.clone(), decode_result)
            })
            .collect()
    }

    pub fn batch_decode(
        &self,
        batches: Vec<Vec<u8>>,
    ) -> Vec<Result<Vec<i32>, String>> {
        batches
            .into_par_iter()
            .map(|data| {
                let mut decoder = Steim2Decoder::new();
                let aligned_data = Steim2Decoder::validate_alignment(&data);
                
                match decoder.add_frames(&aligned_data) {
                    Ok(_) => Ok(decoder.decode_all()),
                    Err(e) => Err(format!("Decode error: {:?}", e)),
                }
            })
            .collect()
    }

    pub fn parallel_quality_filter(
        &self,
        station_samples: &HashMap<String, Vec<i32>>,
        min_quality_score: f64,
        gap_threshold: i32,
    ) -> HashMap<String, (Vec<i32>, PQLXMetrics)> {
        station_samples
            .par_iter()
            .filter_map(|(station_id, samples)| {
                let metrics = PQLXAnalyzer::analyze(samples, gap_threshold);
                let score = PQLXAnalyzer::quality_score(&metrics);
                
                if score >= min_quality_score {
                    Some((station_id.clone(), (samples.clone(), metrics)))
                } else {
                    None
                }
            })
            .collect()
    }
}

impl Default for ParallelProcessor {
    fn default() -> Self {
        Self::new(None)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_processor_creation() {
        let processor = ParallelProcessor::new(Some(4));
        assert!(processor.num_threads.is_some());
    }
}
