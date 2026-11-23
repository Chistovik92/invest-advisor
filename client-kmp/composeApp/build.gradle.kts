import org.jetbrains.compose.desktop.application.dsl.TargetFormat

plugins {
    kotlin("multiplatform")
    kotlin("plugin.compose")
    kotlin("plugin.serialization")
    id("com.android.application")
    id("org.jetbrains.compose")
}

kotlin {
    androidTarget {
        compilations.all {
            kotlinOptions {
                jvmTarget = "17"
            }
        }
    }

    jvm("desktop")

    sourceSets {
        val commonMain by getting {
            dependencies {
                implementation(compose.runtime)
                implementation(compose.foundation)
                implementation(compose.material3)
                implementation(compose.ui)
                implementation("io.ktor:ktor-client-core:2.3.12")
                implementation("io.ktor:ktor-client-content-negotiation:2.3.12")
                implementation("io.ktor:ktor-serialization-kotlinx-json:2.3.12")
                implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.7.3")
                implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:1.9.0")
            }
        }
        val commonTest by getting {
            dependencies {
                implementation(kotlin("test"))
            }
        }
        val androidMain by getting {
            dependencies {
                implementation("androidx.activity:activity-compose:1.9.2")
                implementation("io.ktor:ktor-client-okhttp:2.3.12")
            }
        }
        val desktopMain by getting {
            dependencies {
                implementation(compose.desktop.currentOs)
                implementation("io.ktor:ktor-client-cio:2.3.12")
            }
        }
    }
}

android {
    namespace = "ru.secrethero.invest"
    compileSdk = 34
    defaultConfig {
        applicationId = "ru.secrethero.invest"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "2.0.0"
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

compose.desktop {
    application {
        mainClass = "ru.secrethero.invest.MainKt"
        nativeDistributions {
            targetFormats(
                TargetFormat.Msi,
                TargetFormat.Exe,
                TargetFormat.Deb,
                TargetFormat.Rpm,
                TargetFormat.AppImage
            )
            packageName = "InvestAdvisor"
            packageVersion = "1.0.0"
            description = "Multi-broker portfolio rebalancer for RU market"
            vendor = "SecretHero"

            linux {
                packageName = "invest-advisor"
                debMaintainer = "chistovik92@yandex.ru"
                menuGroup = "Finance"
                appCategory = "Finance"
                iconFile.set(project.file("src/desktopMain/resources/icon.png"))
            }
            windows {
                menuGroup = "InvestAdvisor"
                upgradeUuid = "9a7b6c5d-4e3f-2a1b-8c9d-0e1f2a3b4c5d"
                iconFile.set(project.file("src/desktopMain/resources/icon.ico"))
            }
        }
    }
}
