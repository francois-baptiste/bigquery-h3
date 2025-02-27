use h3o::{LatLng, Resolution};
use std::panic;

// Fonction pour convertir latitude/longitude en index H3, retournant uniquement les 32 bits supérieurs
#[unsafe(no_mangle)]
pub extern "C" fn lat_lng_to_h3_high(lat: f64, lng: f64, resolution: u8) -> u64 {
    // Capture les panics pour éviter de crasher le runtime WebAssembly
    let result = panic::catch_unwind(|| {
        let lat_lng = LatLng::new(lat, lng).expect("Invalid lat/lng");
        let res = Resolution::try_from(resolution).expect("Invalid resolution");
        let cell = lat_lng.to_cell(res);

        // Convertir l'index en u64 en utilisant la méthode appropriée
        let h3_index = u64::from(cell);

        // Retourne uniquement les 32 bits supérieurs
        (h3_index >> 12) as u32
    });

    match result {
        Ok(high) => high,
        Err(_) => 0, // Retourne zéro en cas d'erreur
    }
}
