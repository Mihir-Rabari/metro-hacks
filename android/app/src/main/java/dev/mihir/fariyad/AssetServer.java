package dev.mihir.fariyad;

import android.content.res.AssetManager;
import android.net.Uri;
import android.webkit.WebResourceResponse;

import java.util.HashMap;
import java.util.Map;

/**
 * Serves the bundled web app from APK assets under https://fariyad.local/ —
 * giving the page a proper secure origin without any network access.
 * (IndexedDB, WASM and ES-module imports all require a real origin.)
 */
public final class AssetServer {

    public static final String ORIGIN = "https://fariyad.local";

    private static final Map<String, String> MIME = new HashMap<>();
    static {
        MIME.put("html", "text/html");
        MIME.put("js", "text/javascript");
        MIME.put("css", "text/css");
        MIME.put("json", "application/json");
        MIME.put("onnx", "application/octet-stream");
        MIME.put("wasm", "application/wasm");
        MIME.put("png", "image/png");
        MIME.put("svg", "image/svg+xml");
        MIME.put("txt", "text/plain");
    }

    private AssetServer() {}

    public static WebResourceResponse serve(AssetManager assets, Uri url) {
        if (url == null) return null;
        String s = url.toString();
        if (!s.startsWith(ORIGIN)) return null; // not ours → default WebView handling
        String path = s.substring(ORIGIN.length());
        if (path.startsWith("/")) path = path.substring(1);
        int q = path.indexOf('?');
        if (q >= 0) path = path.substring(0, q);
        if (path.isEmpty()) path = "index.html";
        try {
            java.io.InputStream in = assets.open("www/" + path);
            String ext = path.substring(path.lastIndexOf('.') + 1).toLowerCase();
            String mime = MIME.containsKey(ext) ? MIME.get(ext) : "application/octet-stream";
            String enc = mime.startsWith("text/") ? "utf-8" : null;
            // no caching headers needed: it is a local asset store
            return new WebResourceResponse(mime, enc, in);
        } catch (Exception notFound) {
            return null;
        }
    }
}
