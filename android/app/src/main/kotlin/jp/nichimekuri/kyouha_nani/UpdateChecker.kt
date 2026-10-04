package jp.nichimekuri.kyouha_nani

import android.content.Context
import android.os.Build
import android.util.Log
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/** Reads version.json from GitHub Pages so the app can mention a newer APK. */
object UpdateChecker {
    private const val VERSION_URL = "https://tngmshr.github.io/daily365-wallpaper/version.json"
    private const val PREFS = "daily365_update"
    private const val CHECKED_AT = "checked_at"
    private const val LATEST_JSON = "latest_json"
    private const val DISMISSED_BUILD = "dismissed_build"
    private const val CHECK_INTERVAL_MS = 12 * 60 * 60 * 1000L

    @Synchronized
    fun check(context: Context, force: Boolean = false): Map<String, Any?> {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val now = System.currentTimeMillis()
        if (force || now - prefs.getLong(CHECKED_AT, 0L) >= CHECK_INTERVAL_MS) {
            try {
                val body = fetch()
                JSONObject(body) // Reject malformed payloads before caching them.
                prefs.edit().putLong(CHECKED_AT, now).putString(LATEST_JSON, body).apply()
            } catch (failure: Exception) {
                // Offline or Pages not yet updated: keep the last known result.
                Log.w("DailyUpdate", "Version check failed: ${failure.message}")
            }
        }
        val latest = prefs.getString(LATEST_JSON, null)?.let {
            try { JSONObject(it) } catch (_: Exception) { null }
        }
        val notes = latest?.optJSONArray("notes")
        return mapOf(
            "currentBuild" to currentBuild(context),
            "latestBuild" to (latest?.optInt("build", 0) ?: 0),
            "latestVersion" to (latest?.optString("version", "") ?: ""),
            "notes" to (0 until (notes?.length() ?: 0)).map { notes!!.optString(it) },
            "dismissedBuild" to prefs.getInt(DISMISSED_BUILD, 0),
            "is64bit" to (Build.SUPPORTED_64_BIT_ABIS.isNotEmpty()),
        )
    }

    fun dismiss(context: Context, build: Int) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
            .putInt(DISMISSED_BUILD, build).apply()
    }

    private fun fetch(): String {
        val connection = URL(VERSION_URL).openConnection() as HttpURLConnection
        try {
            connection.connectTimeout = 10_000
            connection.readTimeout = 10_000
            connection.instanceFollowRedirects = false
            connection.useCaches = false
            if (connection.responseCode != HttpURLConnection.HTTP_OK) {
                throw IllegalStateException("HTTP ${connection.responseCode}")
            }
            val bytes = connection.inputStream.use { it.readBytes() }
            if (bytes.size > 64 * 1024) throw IllegalStateException("version.json too large")
            return String(bytes, Charsets.UTF_8)
        } finally {
            connection.disconnect()
        }
    }

    // Split-per-ABI builds add 1000/2000 to versionCode; compare the pubspec build only.
    private fun currentBuild(context: Context): Int {
        val info = context.packageManager.getPackageInfo(context.packageName, 0)
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            (info.longVersionCode % 1000).toInt()
        } else {
            @Suppress("DEPRECATION")
            info.versionCode % 1000
        }
    }
}
