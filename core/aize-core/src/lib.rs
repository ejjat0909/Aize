//! Aize navigation core.
//!
//! Pure computation, no I/O and no Android types, so it is testable on the host and
//! can sit behind UniFFI later. Today it holds the polyline codec that the Kotlin
//! app also implements; the two share the same tests (see `app/src/test/.../PolylineTest.kt`).

pub mod polyline;

/// Crate version, for the "about" screen and for logs.
pub fn version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}
