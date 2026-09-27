package jp.nichimekuri.kyouha_nani

import android.os.Handler
import android.os.Looper
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    private val channelName = "daily365/wallpaper"

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
                    "enableDaily" -> {
                        getSharedPreferences(DailyWallpaperScheduler.PREFS, MODE_PRIVATE)
                            .edit().putBoolean(DailyWallpaperScheduler.ENABLED, true).apply()
                        DailyWallpaperScheduler.scheduleNext(this)
                        DailyWallpaperScheduler.applyToday(this) { error ->
                            Handler(Looper.getMainLooper()).post {
                                if (error == null) result.success(true)
                                else {
                                    getSharedPreferences(DailyWallpaperScheduler.PREFS, MODE_PRIVATE)
                                        .edit().putBoolean(DailyWallpaperScheduler.ENABLED, false).apply()
                                    DailyWallpaperScheduler.cancel(this)
                                    result.error("SET_WALLPAPER_FAILED", error, null)
                                }
                            }
                        }
                    }
                    "disableDaily" -> {
                        getSharedPreferences(DailyWallpaperScheduler.PREFS, MODE_PRIVATE)
                            .edit().putBoolean(DailyWallpaperScheduler.ENABLED, false).apply()
                        DailyWallpaperScheduler.cancel(this)
                        result.success(true)
                    }
                    "setNow" -> DailyWallpaperScheduler.applyToday(this) { error ->
                        Handler(Looper.getMainLooper()).post {
                            if (error == null) result.success(true)
                            else result.error("SET_WALLPAPER_FAILED", error, null)
                        }
                    }
                    else -> result.notImplemented()
                }
            }
    }
}
