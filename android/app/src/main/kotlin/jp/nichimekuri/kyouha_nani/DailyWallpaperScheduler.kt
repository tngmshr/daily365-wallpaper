package jp.nichimekuri.kyouha_nani

import android.app.AlarmManager
import android.app.PendingIntent
import android.app.WallpaperManager
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.Worker
import androidx.work.WorkerParameters
import java.util.Calendar
import java.util.Locale
import java.util.concurrent.TimeUnit

object DailyWallpaperScheduler {
    const val PREFS = "daily_wallpaper_settings"
    const val ENABLED = "enabled"
    const val TRIGGER_ALARM = "alarm"
    const val TRIGGER_WORKER = "worker"
    const val TRIGGER_RESUME = "resume"
    const val TRIGGER_BOOT = "boot"
    const val TRIGGER_SYSTEM = "system"
    const val TRIGGER_RETRY = "retry"
    const val ACTION_RETRY = "jp.nichimekuri.kyouha_nani.DAILY_WALLPAPER.RETRY"

    private const val LAST_SET_DATE = "last_set_date"
    private const val LAST_SUCCESS_AT = "last_success_at"
    private const val LAST_ATTEMPT_AT = "last_attempt_at"
    private const val LAST_ERROR = "last_error"
    private const val LAST_TRIGGER = "last_trigger"
    private const val DAILY_REQUEST_CODE = 9037
    private const val RETRY_REQUEST_CODE = 9038
    private const val RETRY_DELAY_MILLIS = 15 * 60 * 1000L
    private const val PERIODIC_WORK_NAME = "daily_wallpaper_catch_up"
    const val ACTION_DAILY = "jp.nichimekuri.kyouha_nani.DAILY_WALLPAPER"

    fun scheduleNext(context: Context) {
        if (!isEnabled(context)) return
        val next = Calendar.getInstance().apply {
            set(Calendar.HOUR_OF_DAY, 0)
            set(Calendar.MINUTE, 0)
            set(Calendar.SECOND, 30)
            set(Calendar.MILLISECOND, 0)
            if (timeInMillis <= System.currentTimeMillis()) add(Calendar.DAY_OF_YEAR, 1)
        }
        try {
            setAlarm(context, next.timeInMillis, dailyPendingIntent(context))
        } catch (failure: Exception) {
            recordSchedulingError(context, "Daily alarm scheduling failed", failure)
        }
    }

    fun schedulePeriodicWork(context: Context) {
        if (!isEnabled(context)) return
        try {
            val request = PeriodicWorkRequestBuilder<DailyWallpaperWorker>(1, TimeUnit.HOURS).build()
            WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                PERIODIC_WORK_NAME,
                ExistingPeriodicWorkPolicy.KEEP,
                request,
            )
        } catch (failure: Exception) {
            recordSchedulingError(context, "Periodic worker scheduling failed", failure)
        }
    }

    fun cancel(context: Context) {
        val alarmManager = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager
        alarmManager.cancel(dailyPendingIntent(context))
        cancelRetry(context)
    }

    fun cancelPeriodicWork(context: Context) {
        WorkManager.getInstance(context).cancelUniqueWork(PERIODIC_WORK_NAME)
    }

    @Synchronized
    fun ensureToday(context: Context, trigger: String = "unknown") {
        if (!isEnabled(context)) return
        recordAttempt(context, trigger)
        try {
            val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            if (prefs.getString(LAST_SET_DATE, null) != todayKey(Calendar.getInstance())) {
                setToday(context)
            } else {
                cancelRetry(context)
            }
        } catch (failure: Exception) {
            recordFailure(context, failure)
            scheduleRetry(context)
            throw failure
        } finally {
            scheduleNext(context)
        }
    }

    @Synchronized
    fun retryFailedSet(context: Context) {
        if (!isEnabled(context)) return
        recordAttempt(context, TRIGGER_RETRY)
        try {
            setToday(context)
        } catch (failure: Exception) {
            recordFailure(context, failure)
            scheduleRetry(context)
        } finally {
            scheduleNext(context)
        }
    }

    fun applyToday(context: Context, trigger: String, finished: (String?) -> Unit) {
        Thread {
            recordAttempt(context, trigger)
            val error = try {
                setToday(context)
                null
            } catch (failure: Exception) {
                recordFailure(context, failure)
                scheduleRetry(context)
                failure.message ?: "Today's wallpaper is not available yet."
            }
            finished(error)
        }.start()
    }

    fun status(context: Context): Map<String, Any?> {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val powerManager = context.getSystemService(Context.POWER_SERVICE) as android.os.PowerManager
        val exactAlarmsAllowed = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            (context.getSystemService(Context.ALARM_SERVICE) as AlarmManager).canScheduleExactAlarms()
        } else {
            true
        }
        return mapOf(
            "enabled" to prefs.getBoolean(ENABLED, false),
            "lastSuccessAt" to prefs.getLong(LAST_SUCCESS_AT, 0L),
            "lastAttemptAt" to prefs.getLong(LAST_ATTEMPT_AT, 0L),
            "lastError" to prefs.getString(LAST_ERROR, null),
            "lastTrigger" to prefs.getString(LAST_TRIGGER, null),
            "isIgnoringBatteryOptimizations" to if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                powerManager.isIgnoringBatteryOptimizations(context.packageName)
            } else {
                true
            },
            "manufacturer" to Build.MANUFACTURER,
            "exactAlarmsAllowed" to exactAlarmsAllowed,
        )
    }

    private fun setAlarm(context: Context, atMillis: Long, pendingIntent: PendingIntent) {
        val alarmManager = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            val exactAllowed = Build.VERSION.SDK_INT < Build.VERSION_CODES.S ||
                alarmManager.canScheduleExactAlarms()
            if (exactAllowed) {
                try {
                    alarmManager.setExactAndAllowWhileIdle(
                        AlarmManager.RTC_WAKEUP,
                        atMillis,
                        pendingIntent,
                    )
                    return
                } catch (_: SecurityException) {
                    // Permission may have changed after the capability check.
                }
            }
            alarmManager.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, atMillis, pendingIntent)
        } else {
            alarmManager.set(AlarmManager.RTC_WAKEUP, atMillis, pendingIntent)
        }
    }

    private fun scheduleRetry(context: Context) {
        try {
            setAlarm(
                context,
                System.currentTimeMillis() + RETRY_DELAY_MILLIS,
                retryPendingIntent(context),
            )
        } catch (failure: Exception) {
            recordSchedulingError(context, "Retry alarm scheduling failed", failure)
        }
    }

    private fun cancelRetry(context: Context) {
        val alarmManager = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager
        alarmManager.cancel(retryPendingIntent(context))
    }

    private fun dailyPendingIntent(context: Context): PendingIntent = pendingIntent(
        context,
        DAILY_REQUEST_CODE,
        ACTION_DAILY,
    )

    private fun retryPendingIntent(context: Context): PendingIntent = pendingIntent(
        context,
        RETRY_REQUEST_CODE,
        ACTION_RETRY,
    )

    private fun pendingIntent(context: Context, requestCode: Int, action: String): PendingIntent {
        val intent = Intent(context, DailyWallpaperReceiver::class.java).setAction(action)
        val flags = PendingIntent.FLAG_UPDATE_CURRENT or
            (if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) PendingIntent.FLAG_IMMUTABLE else 0)
        return PendingIntent.getBroadcast(context, requestCode, intent, flags)
    }

    private fun isEnabled(context: Context): Boolean = context
        .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        .getBoolean(ENABLED, false)

    private fun todayKey(day: Calendar): String = "%04d-%02d-%02d".format(
        Locale.ROOT,
        day.get(Calendar.YEAR),
        day.get(Calendar.MONTH) + 1,
        day.get(Calendar.DAY_OF_MONTH),
    )

    @Synchronized
    private fun setToday(context: Context) {
        val day = Calendar.getInstance()
        val name = "%02d-%02d.webp".format(
            Locale.ROOT,
            day.get(Calendar.MONTH) + 1,
            day.get(Calendar.DAY_OF_MONTH),
        )
        val asset = "flutter_assets/assets/wallpapers/$name"
        context.assets.open(asset).use { stream ->
            val wallpaperManager = WallpaperManager.getInstance(context)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
                wallpaperManager.setStream(stream, null, true, WallpaperManager.FLAG_LOCK)
            } else {
                wallpaperManager.setStream(stream)
            }
        }
        val now = System.currentTimeMillis()
        val saved = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putString(LAST_SET_DATE, todayKey(day))
            .putLong(LAST_SUCCESS_AT, now)
            .remove(LAST_ERROR)
            .commit()
        if (!saved) throw IllegalStateException("Could not save the last wallpaper date.")
        cancelRetry(context)
    }

    private fun recordAttempt(context: Context, trigger: String) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putLong(LAST_ATTEMPT_AT, System.currentTimeMillis())
            .putString(LAST_TRIGGER, trigger)
            .apply()
    }

    private fun recordFailure(context: Context, failure: Exception) {
        val message = failure.message ?: "Today's wallpaper could not be set."
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putString(LAST_ERROR, message)
            .apply()
    }

    private fun recordSchedulingError(context: Context, label: String, failure: Exception) {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val previous = prefs.getString(LAST_ERROR, null)
        val message = "$label: ${failure.message ?: failure.javaClass.simpleName}"
        prefs.edit().putString(
            LAST_ERROR,
            (if (previous.isNullOrBlank()) message else "$previous\n$message").takeLast(2000),
        ).apply()
    }
}

class DailyWallpaperReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val pending = goAsync()
        val action = intent.action
        val trigger = when (action) {
            Intent.ACTION_BOOT_COMPLETED,
            Intent.ACTION_MY_PACKAGE_REPLACED -> DailyWallpaperScheduler.TRIGGER_BOOT
            Intent.ACTION_TIME_CHANGED,
            Intent.ACTION_TIMEZONE_CHANGED -> DailyWallpaperScheduler.TRIGGER_SYSTEM
            DailyWallpaperScheduler.ACTION_RETRY -> DailyWallpaperScheduler.TRIGGER_RETRY
            else -> DailyWallpaperScheduler.TRIGGER_ALARM
        }
        try {
            Thread {
                try {
                    if (context.getSharedPreferences(DailyWallpaperScheduler.PREFS, Context.MODE_PRIVATE)
                            .getBoolean(DailyWallpaperScheduler.ENABLED, false)
                    ) {
                        try {
                            DailyWallpaperScheduler.schedulePeriodicWork(context.applicationContext)
                        } catch (_: Exception) {
                            // The daily alarm and app resume remain available as fallbacks.
                        }
                    }
                    if (trigger == DailyWallpaperScheduler.TRIGGER_RETRY) {
                        DailyWallpaperScheduler.retryFailedSet(context.applicationContext)
                    } else {
                        DailyWallpaperScheduler.ensureToday(context.applicationContext, trigger)
                    }
                } catch (_: Exception) {
                    // The retry alarm, periodic worker, or next app resume can try again.
                } finally {
                    pending.finish()
                }
            }.start()
        } catch (failure: Exception) {
            pending.finish()
            throw failure
        }
    }
}

class DailyWallpaperWorker(context: Context, params: WorkerParameters) : Worker(context, params) {
    override fun doWork(): Result = try {
        DailyWallpaperScheduler.ensureToday(applicationContext, DailyWallpaperScheduler.TRIGGER_WORKER)
        Result.success()
    } catch (_: Exception) {
        Result.retry()
    }
}
