fn main() {
    let mut build = cc::Build::new();
    build
        .cpp(true)
        .file("../cpp_core/src/ms_peak_detector.cpp")
        .include("../cpp_core/include")
        .flag_if_supported("-std=c++17")
        .flag_if_supported("-O3")
        .flag_if_supported("-march=native")
        .opt_level(3);

    #[cfg(target_os = "windows")]
    {
        build.flag_if_supported("/EHsc");
    }

    build.compile("ms_peak_detector_cpp");

    println!("cargo:rerun-if-changed=../cpp_core/include/ms_peak_detector.h");
    println!("cargo:rerun-if-changed=../cpp_core/src/ms_peak_detector.cpp");
}
