import javax.inject.Inject

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.compose)
}

android {
    namespace = "app.aize"
    compileSdk = 37

    defaultConfig {
        applicationId = "app.aize"
        minSdk = 26            // dev default; decision D2 in docs/02-aize-build-plan.md section 0
        targetSdk = 36
        versionCode = 1
        versionName = "0.0.1-p0"
        // arm64 + x86_64 only: no 32-bit ABIs (smaller APK; the emulator on this VM is x86_64)
        ndk { abiFilters += listOf("arm64-v8a", "x86_64") }
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    // The tile archive is read with random access: store it uncompressed so it can be copied/mapped fast.
    androidResources { noCompress += listOf("pmtiles", "webp") }
}

// Single source of truth for the 3D sprites is assets3d/dist: copy the xxhdpi tier at build time, never commit duplicates.
abstract class SyncSprites : DefaultTask() {
    @get:InputDirectory @get:PathSensitive(PathSensitivity.RELATIVE) abstract val dist: DirectoryProperty
    @get:OutputDirectory abstract val out: DirectoryProperty
    @get:Inject abstract val fs: FileSystemOperations

    @TaskAction
    fun sync() {
        fs.sync {
            from(dist) {
                include("arrow/arrow.sprites.json", "arrow/arrow_p*@xxhdpi.webp")
                include("puck/puck.sprites.json", "puck/puck_p*@xxhdpi.webp")
                include("pin_destination/pin_destination.sprites.json", "pin_destination/pin_destination*@xxhdpi.webp")
            }
            into(out.dir("sprites"))
        }
    }
}

val syncSprites = tasks.register<SyncSprites>("syncSprites") {
    dist.set(rootProject.layout.projectDirectory.dir("assets3d/dist"))
    out.set(layout.buildDirectory.dir("generated/aize-assets"))
}

androidComponents {
    onVariants { variant ->
        variant.sources.assets?.addGeneratedSourceDirectory(syncSprites, SyncSprites::out)
        // optional dev map data (data/dev/assets, gitignored; scripts/fetch-dev-tiles.sh creates it)
        val dev = rootProject.file("data/dev/assets")
        if (dev.exists()) variant.sources.assets?.addStaticSourceDirectory(dev.absolutePath)
    }
}

dependencies {
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.lifecycle.runtime.compose)
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.compose.material.icons.core)
    implementation(libs.kotlinx.coroutines.android)
    implementation(libs.maplibre.android)

    testImplementation(libs.junit)
    testImplementation(libs.org.json)
}
