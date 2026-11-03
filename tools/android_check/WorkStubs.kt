// Compile-only stand-ins for the androidx.work API surface the app uses (Google Maven is unreachable here).
package androidx.work

import android.content.Context
import java.util.concurrent.TimeUnit

open class WorkerParameters
abstract class ListenableWorker(val applicationContext: Context, params: WorkerParameters) {
    abstract class Result {
        companion object {
            @JvmStatic fun success(): Result = object : Result() {}
            @JvmStatic fun retry(): Result = object : Result() {}
            @JvmStatic fun failure(): Result = object : Result() {}
        }
    }
}
abstract class Worker(context: Context, params: WorkerParameters) : ListenableWorker(context, params) {
    abstract fun doWork(): Result
}
open class WorkRequest
class PeriodicWorkRequest : WorkRequest()
class PeriodicWorkRequestBuilderImpl { fun build(): PeriodicWorkRequest = PeriodicWorkRequest() }
inline fun <reified W : ListenableWorker> PeriodicWorkRequestBuilder(interval: Long, unit: TimeUnit) = PeriodicWorkRequestBuilderImpl()
enum class ExistingPeriodicWorkPolicy { KEEP, REPLACE, UPDATE, CANCEL_AND_REENQUEUE }
open class Operation
abstract class WorkManager {
    abstract fun enqueueUniquePeriodicWork(name: String, policy: ExistingPeriodicWorkPolicy, request: PeriodicWorkRequest): Operation
    abstract fun cancelUniqueWork(name: String): Operation
    companion object { @JvmStatic fun getInstance(context: Context): WorkManager = throw UnsupportedOperationException() }
}
