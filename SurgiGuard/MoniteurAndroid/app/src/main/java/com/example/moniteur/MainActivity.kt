package com.example.moniteur

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import com.example.moniteur.alarm.MedAlarms

class MainActivity : ComponentActivity() {
    private val vm: AppViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        handle(intent)
        setContent { AppRoot(vm) }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handle(intent)
    }

    /** Un appui sur la notification d'alarme ouvre la liste des médicaments. */
    private fun handle(intent: Intent?) {
        if (intent?.getBooleanExtra(MedAlarms.EXTRA_OPEN_MEDS, false) == true) vm.openMedsRequest = true
    }
}
