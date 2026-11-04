//! Aize backend. Empty on purpose until P5 (reports, probes, traffic); the workspace
//! exists now so CI, lint and licence checks cover it from the first commit.

/// Service name reported by health checks and logs.
pub const SERVICE: &str = "aize-api";

#[cfg(test)]
mod tests {
    #[test]
    fn names_itself() {
        assert_eq!(super::SERVICE, "aize-api");
    }
}
