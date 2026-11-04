plugins {
    alias(libs.plugins.android.test)
}

android {
    namespace = "app.aize.benchmark"
    compileSdk = 37

    defaultConfig {
        minSdk = 28            // Macrobenchmark needs API 28+
        targetSdk = 36
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        // This machine has no GPU and only an emulator, so the two warnings that make benchmark results
        // non-representative are suppressed here. Numbers from here are for regressions, not for the store.
        testInstrumentationRunnerArguments["androidx.benchmark.suppressErrors"] = "EMULATOR,NOT-SELF-INSTRUMENTING"
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    // Measure the release-like build of :app
    targetProjectPath = ":app"
    // run the benchmark in its own process, not inside the app under test
    experimentalProperties["android.experimental.self-instrumenting"] = true
    buildTypes {
        create("benchmark") {
            isDebuggable = true
            signingConfig = signingConfigs.getByName("debug")
            matchingFallbacks += listOf("release")
        }
    }
}

dependencies {
    implementation(libs.androidx.test.ext.junit)
    implementation(libs.androidx.test.runner)
    implementation(libs.androidx.benchmark.macro.junit4)
    implementation(libs.junit)
}

androidComponents {
    // This module only has the "benchmark" variant that matters; skip debug to save build time.
    beforeVariants(selector().all()) { it.enable = it.buildType == "benchmark" }
}
