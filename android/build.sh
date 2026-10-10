#!/usr/bin/env bash
# Raw Android build — no Gradle, pure SDK build-tools. Runs on ubuntu-latest
# where the Android SDK is preinstalled. Produces a signed Fariyad.apk.
set -euo pipefail

SDK="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-/usr/local/lib/android/sdk}}"
BT="$(ls -d "$SDK"/build-tools/* | sort -V | tail -1)"
PLATFORM="$(ls -d "$SDK"/platforms/android-* | sort -V | tail -1)/android.jar"
cd "$(dirname "$0")"

echo "== build-tools: $BT"
echo "== platform:    $PLATFORM"

# 1) stage the baked web app into assets
cp -f ../dist/app.html app/src/main/assets/www/index.html

# 2) fetch the on-device multilingual model (HF, public, no auth) if absent.
#    Non-fatal: if HF is unreachable the APK ships NB-only (graceful, by design).
MODEL_DIR="app/src/main/assets/www/models/multilingual-minilm"
BASE="https://huggingface.co/Xenova/paraphrase-multilingual-MiniLM-L12-v2/resolve/main"
mkdir -p "$MODEL_DIR/onnx"
if [ ! -s "$MODEL_DIR/onnx/model_quantized.onnx" ]; then
  echo "== downloading model_quantized.onnx (118 MB)"
  if curl -sL --fail --retry 2 -o "$MODEL_DIR/onnx/model_quantized.onnx" "$BASE/onnx/model_quantized.onnx"; then
    echo "== model staged"
  else
    echo "!! model download failed — APK will ship NB-only (neural.js falls back gracefully)"
    rm -f "$MODEL_DIR/onnx/model_quantized.onnx"
  fi
else
  echo "== model already staged"
fi
for f in config.json tokenizer.json tokenizer_config.json special_tokens_map.json; do
  if [ ! -s "$MODEL_DIR/$f" ]; then
    curl -sL --fail -o "$MODEL_DIR/$f" "$BASE/$f"
  fi
done
echo "== model staged: $(du -sh "$MODEL_DIR" | cut -f1)"

# 3) compile resources
rm -f res.zip unsigned.apk aligned.apk Fariyad.apk
"$BT/aapt2" compile --dir app/src/main/res -o res.zip

# 4) link manifest + resources
"$BT/aapt2" link -o unsigned.apk -I "$PLATFORM" \
  --manifest app/src/main/AndroidManifest.xml \
  --min-sdk-version 24 --target-sdk-version 34 \
  --version-code "${GITHUB_RUN_NUMBER:-1}" --version-name "1.0" \
  res.zip

# 5) compile java (warnings about bootclasspath are expected)
rm -rf obj dexout
mkdir -p obj dexout
javac -source 11 -target 11 -classpath "$PLATFORM" -d obj \
  $(find app/src/main/java -name '*.java')

# 6) dex
"$BT/d8" --lib "$PLATFORM" --release --output dexout $(find obj -name '*.class')

# 7) pack dex + assets into the apk (paths relative to the android/ build dir)
BUILD_DIR="$(pwd)"
(cd dexout && zip -q "$BUILD_DIR/unsigned.apk" classes.dex)
# AssetManager resolves entries under assets/ — zip from app/src/main so the
# APK path is assets/www/... (zipping from inside assets/ put www/ at the APK
# root, where AssetServer can't serve it: white-screen on launch).
(cd app/src/main && zip -qr "$BUILD_DIR/unsigned.apk" assets)

# 8) zipalign
"$BT/zipalign" -f 4 unsigned.apk aligned.apk

# 9) sign with a generated key (debug-style; install via "unknown apps")
if [ ! -f debug.keystore ]; then
  keytool -genkeypair -keystore debug.keystore -alias fariyad \
    -storepass fariyad123 -keypass fariyad123 \
    -dname "CN=Fariyad,O=MetroHacks,C=IN" -keyalg RSA -keysize 2048 -validity 10000
fi
"$BT/apksigner" sign --ks debug.keystore --ks-pass pass:fariyad123 \
  --ks-key-alias fariyad --key-pass pass:fariyad123 \
  --out Fariyad.apk aligned.apk

echo "== APK_SIZE: $(du -h Fariyad.apk | cut -f1)"
echo "== sha256:   $(sha256sum Fariyad.apk | cut -d' ' -f1)"
