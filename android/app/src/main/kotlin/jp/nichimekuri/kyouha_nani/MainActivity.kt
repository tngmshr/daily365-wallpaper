package jp.nichimekuri.kyouha_nani

import android.content.ComponentName
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    private val channelName = "daily365/wallpaper"

    override fun onResume() {
        super.onResume()
        Thread {
            try {
                DailyWallpaperScheduler.ensureToday(
                    applicationContext,
                    DailyWallpaperScheduler.TRIGGER_RESUME,
                )
            } catch (_: Exception) {
                // The retry alarm, periodic worker, or next app resume can try again.
            }
        }.start()
    }

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, channelName)
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "isEnabled" -> {
                        val enabled = getSharedPreferences(DailyWallpaperScheduler.PREFS, MODE_PRIVATE)
                            .getBoolean(DailyWallpaperScheduler.ENABLED, false)
                        result.success(enabled)
                    }
                    "status" -> result.success(DailyWallpaperScheduler.status(this))
                    "enableDaily" -> {
                        getSharedPreferences(DailyWallpaperScheduler.PREFS, MODE_PRIVATE)
                            .edit().putBoolean(DailyWallpaperScheduler.ENABLED, true).apply()
                        DailyWallpaperScheduler.scheduleNext(this)
                        DailyWallpaperScheduler.schedulePeriodicWork(this)
                        DailyWallpaperScheduler.applyToday(this, "enable") { error ->
                            Handler(Looper.getMainLooper()).post {
                                if (error == null) {
                                    result.success(true)
                                } else {
                                    getSharedPreferences(DailyWallpaperScheduler.PREFS, MODE_PRIVATE)
                                        .edit().putBoolean(DailyWallpaperScheduler.ENABLED, false).apply()
                                    DailyWallpaperScheduler.cancel(this)
                                    DailyWallpaperScheduler.cancelPeriodicWork(this)
                                    result.error("SET_WALLPAPER_FAILED", error, null)
                                }
                            }
                        }
                    }
                    "disableDaily" -> {
                        getSharedPreferences(DailyWallpaperScheduler.PREFS, MODE_PRIVATE)
                            .edit().putBoolean(DailyWallpaperScheduler.ENABLED, false).apply()
                        DailyWallpaperScheduler.cancel(this)
                        DailyWallpaperScheduler.cancelPeriodicWork(this)
                        result.success(true)
                    }
                    "setNow" -> DailyWallpaperScheduler.applyToday(this, "setNow") { error ->
                        Handler(Looper.getMainLooper()).post {
                            if (error == null) result.success(true)
                            else result.error("SET_WALLPAPER_FAILED", error, null)
                        }
                    }
                    "requestIgnoreBatteryOptimizations" -> {
                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                            try {
                                startActivity(
                                    Intent(
                                        Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS,
                                        Uri.parse("package:$packageName"),
                                    ),
                                )
                            } catch (failure: Exception) {
                                result.error("SETTINGS_UNAVAILABLE", failure.message, null)
                                return@setMethodCallHandler
                            }
                        }
                        result.success(true)
                    }
                    "openAutostartSettings" -> {
                        val manufacturer = Build.MANUFACTURER.lowercase()
                        if (manufacturer.contains("xiaomi") || manufacturer.contains("redmi") ||
                            manufacturer.contains("poco")
                        ) {
                            try {
                                startActivity(
                                    Intent().setComponent(
                                        ComponentName(
                                            "com.miui.securitycenter",
                                            "com.miui.permcenter.autostart.AutoStartManagementActivity",
                                        ),
                                    ),
                                )
                                result.success(true)
                                return@setMethodCallHandler
                            } catch (_: Exception) {
                                // Fall through to the app details page on HyperOS variants without this screen.
                            }
                        }
                        try {
                            startActivity(
                                Intent(
                                    Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                                    Uri.parse("package:$packageName"),
                                ),
                            )
                            result.success(true)
                        } catch (failure: Exception) {
                            result.error("SETTINGS_UNAVAILABLE", failure.message, null)
                        }
                    }
                    else -> result.notImplemented()
                }
            }
    }
}
