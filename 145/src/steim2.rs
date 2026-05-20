use byteorder::{BigEndian, ReadBytesExt};
use std::io::Cursor;

#[derive(Debug, thiserror::Error)]
pub enum Steim2Error {
    #[error("Invalid frame size: must be 64 bytes")]
    InvalidFrameSize,
    #[error("Invalid encoding format")]
    InvalidEncoding,
    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),
}

#[derive(Debug, Clone, Copy)]
pub struct Steim2Frame {
    data: [u8; 64],
}

impl Steim2Frame {
    pub fn new(data: &[u8]) -> Result<Self, Steim2Error> {
        if data.len() != 64 {
            return Err(Steim2Error::InvalidFrameSize);
        }
        let mut frame = [0u8; 64];
        frame.copy_from_slice(data);
        Ok(Self { data: frame })
    }

    pub fn decode(&self) -> Vec<i32> {
        let mut samples = Vec::with_capacity(100);
        let mut dn = 0i32;
        
        for chunk in self.data.chunks(4) {
            if chunk.len() < 4 {
                break;
            }
            
            let mut cursor = Cursor::new(chunk);
            let word = cursor.read_u32::<BigEndian>().unwrap_or(0);
            
            let ctrl = (word >> 30) & 0x03;
            
            match ctrl {
                0 => {
                    for j in 0..15 {
                        let shift = 28 - j * 2;
                        let diff = ((word >> shift) & 0x03) as i8;
                        let diff = if diff >= 2 { diff - 4 } else { diff };
                        dn += diff as i32;
                        samples.push(dn);
                    }
                }
                1 => {
                    for j in 0..7 {
                        let shift = 26 - j * 4;
                        let diff = ((word >> shift) & 0x0F) as i8;
                        let diff = if diff >= 8 { diff - 16 } else { diff };
                        dn += diff as i32;
                        samples.push(dn);
                    }
                }
                2 => {
                    for j in 0..3 {
                        let shift = 22 - j * 8;
                        let diff = ((word >> shift) & 0xFF) as i16;
                        let diff = if diff >= 128 { diff - 256 } else { diff };
                        dn += diff as i32;
                        samples.push(dn);
                    }
                }
                3 => {
                    let diff = (word & 0x3FFFFFFF) as i32;
                    dn += diff;
                    samples.push(dn);
                }
                _ => {}
            }
        }
        
        samples
    }
}

pub struct Steim2Decoder {
    frames: Vec<Steim2Frame>,
}

impl Steim2Decoder {
    pub fn new() -> Self {
        Self { frames: Vec::new() }
    }

    pub fn add_frame(&mut self, frame_data: &[u8]) -> Result<(), Steim2Error> {
        let frame = Steim2Frame::new(frame_data)?;
        self.frames.push(frame);
        Ok(())
    }

    pub fn add_frames(&mut self, frames_data: &[u8]) -> Result<(), Steim2Error> {
        for chunk in frames_data.chunks(64) {
            if chunk.len() == 64 {
                self.add_frame(chunk)?;
            }
        }
        Ok(())
    }

    pub fn decode_all(&self) -> Vec<i32> {
        let mut samples = Vec::new();
        let mut dn = 0i32;
        
        for frame in &self.frames {
            let mut frame_samples = frame.decode();
            let offset = samples.last().copied().unwrap_or(0);
            for s in &mut frame_samples {
                *s += dn;
            }
            samples.extend(frame_samples);
            dn = *samples.last().copied().unwrap_or(&0);
        }
        
        samples
    }

    pub fn decode_single_frame(frame_data: &[u8]) -> Result<Vec<i32>, Steim2Error> {
        let frame = Steim2Frame::new(frame_data)?;
        Ok(frame.decode())
    }

    pub fn validate_alignment(data: &[u8]) -> Vec<u8> {
        let remainder = data.len() % 64;
        if remainder == 0 {
            data.to_vec()
        } else {
            let padding = 64 - remainder;
            let mut aligned = data.to_vec();
            aligned.extend_from_slice(&vec![0u8; padding]);
            aligned
        }
    }
}

impl Default for Steim2Decoder {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_frame_creation() {
        let data = [0u8; 64];
        let frame = Steim2Frame::new(&data);
        assert!(frame.is_ok());
    }

    #[test]
    fn test_alignment() {
        let data = [0u8; 100];
        let aligned = Steim2Decoder::validate_alignment(&data);
        assert_eq!(aligned.len(), 128);
    }
}
