#!/usr/bin/env bash
# Native Android build — no Gradle, no WebView, pure SDK build-tools + ONNX Runtime.
# Produces a signed FariyadNative.apk. Runs on ubuntu-latest (Android SDK preinstalled).
set -euo pipefail

SDK="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-/usr/local/lib/android/sdk}}"
# Pin to stable 34.x: runners default to build-tools 37.0.0 + android-37.2-beta3,
# whose beta aapt2 mis-validates style-item color references ("expected color but
# got (raw string)"). 34 is preinstalled on ubuntu-latest images.
BT="$(ls -d "$SDK"/build-tools/34* 2>/dev/null | sort -V | tail -1)"
[ -z "$BT" ] && BT="$(ls -d "$SDK"/build-tools/* | sort -V | tail -1)"
PLATFORM="$(ls -d "$SDK"/platforms/android-34* 2>/dev/null | sort -V | tail -1)/android.jar"
[ -e "$PLATFORM" ] || PLATFORM="$(ls -d "$SDK"/platforms/android-* | sort -V | tail -1)/android.jar"
cd "$(dirname "$0")"

ORT_VER="1.16.3"
ORT_AAR="onnxruntime-android-${ORT_VER}.aar"
ORT_URL="https://repo1.maven.org/maven2/com/microsoft/onnxruntime/onnxruntime-android/${ORT_VER}/${ORT_AAR}"

echo "== build-tools: $BT"
echo "== platform:    $PLATFORM"

# ---------------------------------------------------------------- assets
A="app/src/main/assets/models"
mkdir -p "$A"
cp -f ../models/triage.json "$A/triage.json"
cp -f ../data/replies.json "$A/replies.json"
cp -f ../data/stations.json "$A/stations.json"
cp -f ../android/app/src/main/assets/www/models/centroids.json "$A/centroids.json"
cp -f ../android/app/src/main/assets/www/models/multilingual-minilm/tokenizer.json "$A/tokenizer.json"

# icon (shared with the WebView app)
mkdir -p app/src/main/res/mipmap
cp -f ../android/app/src/main/res/mipmap/ic_launcher.png app/src/main/res/mipmap/ic_launcher.png

# ONNX weights: fetched at build time (118 MB — never enters git). Non-fatal:
# without them the app runs the NB engine natively and degrades gracefully.
BASE="https://huggingface.co/Xenova/paraphrase-multilingual-MiniLM-L12-v2/resolve/main"
if [ ! -s "$A/model.onnx" ]; then
  echo "== downloading model_quantized.onnx (118 MB)"
  if curl -sL --fail --retry 2 -o "$A/model.onnx" "$BASE/onnx/model_quantized.onnx"; then
    echo "== model staged"
  else
    echo "!! model download failed — native APK ships NB-only (Neural.java degrades gracefully)"
    rm -f "$A/model.onnx"
  fi
fi

# ---------------------------------------------------------------- ONNX Runtime AAR
if [ ! -s "ort/$ORT_AAR" ]; then
  mkdir -p ort
  echo "== downloading $ORT_AAR"
  curl -sL --fail --retry 3 -o "ort/$ORT_AAR" "$ORT_URL"
fi
rm -rf ort/x && mkdir -p ort/x
(cd ort/x && unzip -q "../$ORT_AAR")
cp ort/x/classes.jar ort/classes.jar
mkdir -p nativelib/lib/arm64-v8a
cp ort/x/jni/arm64-v8a/*.so nativelib/lib/arm64-v8a/
echo "== ORT: $(du -sh ort/classes.jar | cut -f1) classes + $(ls nativelib/lib/arm64-v8a | wc -l) native libs (arm64-v8a)"

# ---------------------------------------------------------------- compile
rm -f res.zip unsigned.apk aligned.apk FariyadNative.apk
rm -rf obj dexout gen && mkdir -p obj dexout gen

"$BT/aapt2" compile --dir app/src/main/res -o res.zip
"$BT/aapt2" link -o unsigned.apk -I "$PLATFORM" \
  --manifest app/src/main/AndroidManifest.xml \
  --min-sdk-version 24 --target-sdk-version 34 \
  --version-code "${GITHUB_RUN_NUMBER:-2}" --version-name "2.0" \
  --java gen \
  res.zip

javac -source 11 -target 11 -classpath "$PLATFORM:ort/classes.jar" -d obj \
  $(find app/src/main/java gen -name '*.java')

"$BT/d8" --lib "$PLATFORM" --release --output dexout \
  $(find obj -name '*.class') ort/classes.jar

# ---------------------------------------------------------------- pack
BUILD_DIR="$(pwd)"
(cd dexout && zip -q "$BUILD_DIR/unsigned.apk" classes.dex)
(cd app/src/main/assets && zip -qr "$BUILD_DIR/unsigned.apk" models)
(cd nativelib && zip -qr "$BUILD_DIR/unsigned.apk" lib)

"$BT/zipalign" -f 4 unsigned.apk aligned.apk

if [ ! -f debug.keystore ]; then
  keytool -genkeypair -keystore debug.keystore -alias fariyad \
    -storepass fariyad123 -keypass fariyad123 \
    -dname "CN=Fariyad,O=MetroHacks,C=IN" -keyalg RSA -keysize 2048 -validity 10000
fi
"$BT/apksigner" sign --ks debug.keystore --ks-pass pass:fariyad123 \
  --ks-key-alias fariyad --key-pass pass:fariyad123 \
  --out FariyadNative.apk aligned.apk

echo "== APK_SIZE: $(du -h FariyadNative.apk | cut -f1)"
echo "== sha256:   $(sha256sum FariyadNative.apk | cut -d' ' -f1)"
