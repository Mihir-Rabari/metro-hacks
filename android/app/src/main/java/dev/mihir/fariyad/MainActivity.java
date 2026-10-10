package dev.mihir.fariyad;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.os.Bundle;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

/**
 * Fariyad — offline grievance console for metro staff.
 * The entire web app (single file + on-device AI model) ships inside the APK
 * and is served from a fake https origin so the page gets a real secure origin:
 * IndexedDB (the offline queue), WASM (on-device transformer) and ES modules all work
 * with ZERO network access.
 */
public class MainActivity extends Activity {

    private WebView web;

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        web = new WebView(this);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);   // IndexedDB + localStorage
        s.setAllowFileAccess(false);    // everything comes from the asset origin
        s.setAllowContentAccess(false);
        s.setMediaPlaybackRequiresUserGesture(false);

        web.setWebViewClient(new WebViewClient() {
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                return AssetServer.serve(getAssets(), request.getUrl());
            }
        });
        web.loadUrl(AssetServer.ORIGIN + "/index.html");
        setContentView(web);
    }

    @Override
    protected void onDestroy() {
        if (web != null) {
            web.loadUrl("about:blank");
            web.destroy();
            web = null;
        }
        super.onDestroy();
    }

    @SuppressWarnings("deprecation")
    @Override
    public void onBackPressed() {
        if (web != null && web.canGoBack()) {
            web.goBack();
        } else {
            super.onBackPressed();
        }
    }
}
