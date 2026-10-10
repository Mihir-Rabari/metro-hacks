package dev.mihir.fariyadnative;

import android.app.Application;

import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;

/**
 * Last-resort crash capture: any uncaught exception on ANY thread (including
 * theme/inflate errors thrown during Activity startup before MainActivity's
 * own try/catch arms) is written to files/crash-log.txt. The next launch shows
 * the log on screen, so a single screenshot pinpoints the cause.
 */
public class App extends Application {
    public static final String CRASH_LOG = "crash-log.txt";

    @Override
    public void onCreate() {
        super.onCreate();
        Thread.setDefaultUncaughtExceptionHandler((thread, throwable) -> {
            try {
                File f = new File(getFilesDir(), CRASH_LOG);
                PrintWriter w = new PrintWriter(new FileWriter(f, true));
                w.println("==== " + new java.util.Date() + "  thread=" + thread.getName());
                throwable.printStackTrace(w);
                w.close();
            } catch (Throwable ignored) {
            }
            android.os.Process.killProcess(android.os.Process.myPid());
            System.exit(2);
        });
    }
}
