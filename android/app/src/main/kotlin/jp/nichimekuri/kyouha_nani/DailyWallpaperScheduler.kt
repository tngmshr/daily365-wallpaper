package jp.nichimekuri.kyouha_nani

import android.app.AlarmManager
import android.app.PendingIntent
import android.app.WallpaperManager
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import java.util.Calendar
import java.util.Locale

object DailyWallpaperScheduler {
    const val PREFS = "daily_wallpaper_settings"
    const val ENABLED = "enabled"
    private const val REQUEST_CODE = 9037
    const val ACTION_DAILY = "jp.nichimekuri.kyouha_nani.DAILY_WALLPAPER"

    fun scheduleNext(context: Context) {
        if (!context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getBoolean(ENABLED, false)) return
        val next = Calendar.getInstance().apply {
            set(Calendar.HOUR_OF_DAY, 7)
            set(Calendar.MINUTE, 0)
            set(Calendar.SECOND, 0)
            set(Calendar.MILLISECOND, 0)
            if (timeInMillis <= System.currentTimeMillis()) add(Calendar.DAY_OF_YEAR, 1)
        }
        val alarmManager = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager
        val pending = pendingIntent(context)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            alarmManager.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, next.timeInMillis, pending)
        } else {
            alarmManager.set(AlarmManager.RTC_WAKEUP, next.timeInMillis, pending)
        }
    }

    fun cancel(context: Context) {
        val alarmManager = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager
        alarmManager.cancel(pendingIntent(context))
    }

    private fun pendingIntent(context: Context): PendingIntent {
        val intent = Intent(context, DailyWallpaperReceiver::class.java).setAction(ACTION_DAILY)
        val flags = PendingIntent.FLAG_UPDATE_CURRENT or
            (if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) PendingIntent.FLAG_IMMUTABLE else 0)
        return PendingIntent.getBroadcast(context, REQUEST_CODE, intent, flags)
    }

    fun applyToday(context: Context, finished: (String?) -> Unit) {
        Thread {
            try {
                val day = Calendar.getInstance()
                val name = "%02d-%02d.jpg".format(
                    Locale.ROOT,
                    day.get(Calendar.MONTH) + 1,
                    day.get(Calendar.DAY_OF_MONTH),
                )
                val asset = "flutter_assets/assets/wallpapers/" + name
                context.assets.open(asset).use { stream ->
                    val wallpaperManager = WallpaperManager.getInstance(context)
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
                        wallpaperManager.setStream(stream, null, true, WallpaperManager.FLAG_LOCK)
                    } else {
                        wallpaperManager.setStream(stream)
                    }
                }
                finished(null)
            } catch (error: Exception) {
                finished(error.message ?: "Today's wallpaper is not available yet.")
            }
        }.start()
    }
}

class DailyWallpaperReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED ||
            intent.action == Intent.ACTION_TIME_CHANGED ||
            intent.action == Intent.ACTION_TIMEZONE_CHANGED
        ) {
            DailyWallpaperScheduler.scheduleNext(context)
            return
        }
        val pending = goAsync()
        DailyWallpaperScheduler.applyToday(context) {
            DailyWallpaperScheduler.scheduleNext(context)
            pending.finish()
        }
    }
}
