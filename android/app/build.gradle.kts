import java.io.File
import java.util.Properties

plugins {
    id("com.android.application")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

dependencies {
    implementation("androidx.work:work-runtime-ktx:2.11.2")
}

val keyPropertiesFile = rootProject.file("key.properties")
val keyProperties = Properties()
if (keyPropertiesFile.isFile) {
    keyPropertiesFile.inputStream().use { keyProperties.load(it) }
}

gradle.taskGraph.whenReady {
    if (!keyPropertiesFile.isFile && allTasks.any { it.name.contains("Release") }) {
        throw GradleException("Release signing requires android/key.properties with storePassword, keyPassword, keyAlias, and an absolute storeFile path.")
    }
}

android {
    namespace = "jp.nichimekuri.kyouha_nani"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    defaultConfig {
        // TODO: Specify your own unique Application ID (https://developer.android.com/studio/build/application-id.html).
        applicationId = "jp.nichimekuri.kyouha_nani"
        // You can update the following values to match your application needs.
        // For more information, see: https://flutter.dev/to/review-gradle-config.
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        // Uses the version code from pubspec.yaml. When using split APKs, 1000 * ABI_VERSION
        // is added automatically by Flutter. (https://developer.android.com/studio/build/configure-apk-splits#configure-APK-versions)
        // You can force using the value of versionCode by specifying the `-P force-version-code-ignoring-abi=true`
        // flag during build.
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

    signingConfigs {
        if (keyPropertiesFile.isFile) {
            create("release") {
                fun required(name: String) = keyProperties.getProperty(name)?.takeIf { it.isNotBlank() }
                    ?: throw GradleException("android/key.properties is missing $name")
                storePassword = required("storePassword")
                keyPassword = required("keyPassword")
                keyAlias = required("keyAlias")
                val keyStore = File(required("storeFile"))
                if (!keyStore.isAbsolute) {
                    throw GradleException("android/key.properties storeFile must be an absolute path")
                }
                if (!keyStore.isFile) {
                    throw GradleException("Release signing key does not exist: $keyStore")
                }
                storeFile = keyStore
            }
        }
    }

    buildTypes {
        release {
            if (keyPropertiesFile.isFile) {
                signingConfig = signingConfigs.getByName("release")
            }
        }
    }
}

kotlin {
    compilerOptions {
        jvmTarget = org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17
    }
}

flutter {
    source = "../.."
}
