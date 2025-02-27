use h3o::{LatLng, Resolution};
use std::panic;

// Function to convert latitude/longitude to H3 index, returning only the upper 52 bits
#[unsafe(no_mangle)]
pub extern "C" fn lat_lng_to_h3(lat: f64, lng: f64, resolution: u8) -> u64 {
    // Capture panics to avoid crashing the WebAssembly runtime
    let result = panic::catch_unwind(|| {
        let lat_lng = LatLng::new(lat, lng).expect("Invalid lat/lng");
        let res = Resolution::try_from(resolution).expect("Invalid resolution");
        let cell = lat_lng.to_cell(res);

        // Convert index to u64
        let h3_index = u64::from(cell);

        const MASK_52_BIT: u64 = (1 << 52) - 1;

        // keep only LSB 52 bits
        h3_index & MASK_52_BIT
    });

    match result {
        Ok(high) => high,
        Err(_) => 0, // Returns zero on error
    }
}
