package com.playoffticker

import android.content.Context
import android.view.View
import android.widget.RemoteViews
import android.widget.RemoteViewsService

class PlayoffWidgetFactory(private val context: Context) : RemoteViewsService.RemoteViewsFactory {

    private var rows: List<SeriesRow> = emptyList()

    override fun onCreate() {}

    override fun onDataSetChanged() {
        // ListView refreshes call this on a background thread — safe to do network I/O.
        rows = if (PlayoffRepository.current().isEmpty()) {
            PlayoffRepository.refreshBlocking()
        } else {
            PlayoffRepository.current()
        }
    }

    override fun onDestroy() {}

    override fun getCount(): Int = rows.size

    override fun getViewAt(position: Int): RemoteViews {
        val r = rows[position]
        val rv = RemoteViews(context.packageName, R.layout.widget_row)
        rv.setTextViewText(R.id.row_league, r.league)
        rv.setTextViewText(R.id.row_matchup, r.matchup)
        rv.setTextViewText(R.id.row_series, r.seriesScore)
        rv.setTextViewText(R.id.row_last_game, r.lastGame)
        if (r.liveStatus != null) {
            rv.setViewVisibility(R.id.row_live, View.VISIBLE)
            rv.setTextViewText(R.id.row_live, r.liveStatus)
        } else {
            rv.setViewVisibility(R.id.row_live, View.GONE)
        }
        return rv
    }

    override fun getLoadingView(): RemoteViews? = null
    override fun getViewTypeCount(): Int = 1
    override fun getItemId(position: Int): Long = position.toLong()
    override fun hasStableIds(): Boolean = true
}
