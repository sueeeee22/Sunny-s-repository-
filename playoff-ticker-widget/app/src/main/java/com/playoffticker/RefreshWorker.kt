package com.playoffticker

import android.appwidget.AppWidgetManager
import android.content.ComponentName
import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class RefreshWorker(ctx: Context, params: WorkerParameters) : CoroutineWorker(ctx, params) {

    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        try {
            PlayoffRepository.refreshBlocking()
            // Tell every widget to redraw and re-bind list data.
            val mgr = AppWidgetManager.getInstance(applicationContext)
            val ids = mgr.getAppWidgetIds(
                ComponentName(applicationContext, PlayoffWidgetProvider::class.java)
            )
            if (ids.isNotEmpty()) {
                PlayoffWidgetProvider.pushAll(applicationContext)
                mgr.notifyAppWidgetViewDataChanged(ids, R.id.widget_list)
            }
            Result.success()
        } catch (e: Exception) {
            Result.retry()
        }
    }
}
