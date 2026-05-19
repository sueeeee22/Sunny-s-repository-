package com.playoffticker

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.widget.RemoteViews
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.ExistingWorkPolicy
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.TimeUnit

class PlayoffWidgetProvider : AppWidgetProvider() {

    companion object {
        const val ACTION_REFRESH = "com.playoffticker.ACTION_REFRESH"
        private const val PERIODIC_WORK = "playoff_refresh_periodic"
        private const val ONCE_WORK = "playoff_refresh_once"

        fun pushAll(context: Context) {
            val mgr = AppWidgetManager.getInstance(context)
            val ids = mgr.getAppWidgetIds(ComponentName(context, PlayoffWidgetProvider::class.java))
            ids.forEach { pushUpdate(context, mgr, it) }
            if (ids.isNotEmpty()) {
                mgr.notifyAppWidgetViewDataChanged(ids, R.id.widget_list)
            }
        }

        private fun pushUpdate(context: Context, mgr: AppWidgetManager, widgetId: Int) {
            val views = RemoteViews(context.packageName, R.layout.widget_playoff)

            val svc = Intent(context, PlayoffWidgetService::class.java).apply {
                putExtra(AppWidgetManager.EXTRA_APPWIDGET_ID, widgetId)
                // make the intent unique per widget so list state is isolated
                data = Uri.parse(toUri(Intent.URI_INTENT_SCHEME))
            }
            views.setRemoteAdapter(R.id.widget_list, svc)
            views.setEmptyView(R.id.widget_list, R.id.widget_empty)

            val refreshIntent = Intent(context, PlayoffWidgetProvider::class.java).apply {
                action = ACTION_REFRESH
            }
            val refreshPi = PendingIntent.getBroadcast(
                context, 0, refreshIntent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
            views.setOnClickPendingIntent(R.id.widget_refresh, refreshPi)
            views.setOnClickPendingIntent(R.id.widget_title, refreshPi)

            val stamp = if (PlayoffRepository.lastUpdatedMillis > 0) {
                SimpleDateFormat("h:mm a", Locale.getDefault())
                    .format(Date(PlayoffRepository.lastUpdatedMillis))
            } else "—"
            views.setTextViewText(R.id.widget_updated, "↻ $stamp")

            mgr.updateAppWidget(widgetId, views)
        }
    }

    override fun onUpdate(
        context: Context,
        appWidgetManager: AppWidgetManager,
        appWidgetIds: IntArray
    ) {
        appWidgetIds.forEach { pushUpdate(context, appWidgetManager, it) }
        enqueueImmediateRefresh(context)
        schedulePeriodicRefresh(context)
    }

    override fun onReceive(context: Context, intent: Intent) {
        super.onReceive(context, intent)
        if (intent.action == ACTION_REFRESH) {
            enqueueImmediateRefresh(context)
        }
    }

    override fun onEnabled(context: Context) {
        super.onEnabled(context)
        enqueueImmediateRefresh(context)
        schedulePeriodicRefresh(context)
    }

    override fun onDisabled(context: Context) {
        super.onDisabled(context)
        WorkManager.getInstance(context).cancelUniqueWork(PERIODIC_WORK)
    }

    private fun enqueueImmediateRefresh(context: Context) {
        val req = OneTimeWorkRequestBuilder<RefreshWorker>().build()
        WorkManager.getInstance(context).enqueueUniqueWork(
            ONCE_WORK, ExistingWorkPolicy.REPLACE, req
        )
    }

    private fun schedulePeriodicRefresh(context: Context) {
        val req = PeriodicWorkRequestBuilder<RefreshWorker>(15, TimeUnit.MINUTES).build()
        WorkManager.getInstance(context).enqueueUniquePeriodicWork(
            PERIODIC_WORK, ExistingPeriodicWorkPolicy.KEEP, req
        )
    }
}
