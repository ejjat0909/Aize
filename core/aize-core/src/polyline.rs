//! Encoded-polyline codec. Valhalla uses precision 6 (1e-6 degrees).

/// Decoded line: parallel latitude and longitude arrays in degrees.
#[derive(Debug, Clone, PartialEq, Default)]
pub struct Line {
    pub lat: Vec<f64>,
    pub lon: Vec<f64>,
}

impl Line {
    pub fn len(&self) -> usize {
        self.lat.len()
    }

    pub fn is_empty(&self) -> bool {
        self.lat.is_empty()
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DecodeError {
    /// The string ended in the middle of a value.
    Truncated,
    /// A character outside the polyline alphabet (63..=126).
    BadChar,
}

impl std::fmt::Display for DecodeError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            DecodeError::Truncated => f.write_str("truncated polyline"),
            DecodeError::BadChar => f.write_str("character outside the polyline alphabet"),
        }
    }
}

impl std::error::Error for DecodeError {}

fn next_delta(bytes: &[u8], i: &mut usize) -> Result<i64, DecodeError> {
    let mut result: i64 = 0;
    let mut shift = 0u32;
    loop {
        let c = *bytes.get(*i).ok_or(DecodeError::Truncated)?;
        *i += 1;
        if !(63..=126).contains(&c) {
            return Err(DecodeError::BadChar);
        }
        let b = i64::from(c) - 63;
        result |= (b & 0x1f) << shift;
        shift += 5;
        if b < 0x20 {
            break;
        }
        if shift > 60 {
            return Err(DecodeError::BadChar);
        }
    }
    Ok(if result & 1 != 0 {
        !(result >> 1)
    } else {
        result >> 1
    })
}

/// Decode `encoded` at `precision` decimal places (5 for the classic format, 6 for Valhalla).
pub fn decode(encoded: &str, precision: u32) -> Result<Line, DecodeError> {
    let factor = 10f64.powi(precision as i32);
    let bytes = encoded.as_bytes();
    let mut line = Line {
        lat: Vec::with_capacity(bytes.len() / 4),
        lon: Vec::with_capacity(bytes.len() / 4),
    };
    let (mut i, mut lat, mut lon) = (0usize, 0i64, 0i64);
    while i < bytes.len() {
        lat += next_delta(bytes, &mut i)?;
        lon += next_delta(bytes, &mut i)?;
        line.lat.push(lat as f64 / factor);
        line.lon.push(lon as f64 / factor);
    }
    Ok(line)
}

fn put(out: &mut String, delta: i64) {
    let mut v = if delta < 0 { !(delta << 1) } else { delta << 1 } as u64;
    while v >= 0x20 {
        out.push((((v & 0x1f) | 0x20) as u8 + 63) as char);
        v >>= 5;
    }
    out.push((v as u8 + 63) as char);
}

/// Encode a line; used by tests and tooling, the app only decodes.
pub fn encode(line: &Line, precision: u32) -> String {
    let factor = 10f64.powi(precision as i32);
    let mut out = String::new();
    let (mut p_lat, mut p_lon) = (0i64, 0i64);
    for (la, lo) in line.lat.iter().zip(&line.lon) {
        let (a, o) = ((la * factor).round() as i64, (lo * factor).round() as i64);
        put(&mut out, a - p_lat);
        put(&mut out, o - p_lon);
        (p_lat, p_lon) = (a, o);
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn close(a: &[f64], b: &[f64]) {
        assert_eq!(a.len(), b.len());
        for (x, y) in a.iter().zip(b) {
            assert!((x - y).abs() < 1e-9, "{x} vs {y}");
        }
    }

    #[test]
    fn decodes_the_canonical_precision_5_example_from_the_polyline_spec() {
        let d = decode("_p~iF~ps|U_ulLnnqC_mqNvxq`@", 5).unwrap();
        close(&d.lat, &[38.5, 40.7, 43.252]);
        close(&d.lon, &[-120.2, -120.95, -126.453]);
    }

    #[test]
    fn round_trip_at_precision_6_with_negative_coordinates_and_long_jumps() {
        let line = Line {
            lat: vec![3.134300, 3.134301, -33.868820, 89.999999, 0.0, -0.000001],
            lon: vec![
                101.686200,
                101.686199,
                151.209296,
                -179.999999,
                0.0,
                179.999999,
            ],
        };
        let d = decode(&encode(&line, 6), 6).unwrap();
        close(&d.lat, &line.lat);
        close(&d.lon, &line.lon);
    }

    #[test]
    fn empty_string_is_an_empty_line_and_a_truncated_one_is_rejected() {
        assert!(decode("", 6).unwrap().is_empty());
        assert_eq!(decode("_p~iF~ps|U_", 6), Err(DecodeError::Truncated));
    }

    #[test]
    fn rejects_characters_outside_the_alphabet() {
        assert_eq!(decode("_p~iF ps|U", 6), Err(DecodeError::BadChar));
    }

    #[test]
    fn handles_long_routes() {
        let n = 5000;
        let line = Line {
            lat: (0..n).map(|i| 3.0 + f64::from(i) * 1e-5).collect(),
            lon: (0..n).map(|i| 101.0 + f64::from(i) * 2e-5).collect(),
        };
        assert_eq!(decode(&encode(&line, 6), 6).unwrap().len(), n as usize);
    }
}
