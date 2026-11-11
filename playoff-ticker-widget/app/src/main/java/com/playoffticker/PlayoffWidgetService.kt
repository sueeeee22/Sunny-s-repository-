package com.playoffticker

import android.content.Intent
import android.widget.RemoteViewsService

class PlayoffWidgetService : RemoteViewsService() {
    override fun onGetViewFactory(intent: Intent): RemoteViewsFactory =
        PlayoffWidgetFactory(applicationContext)
}
