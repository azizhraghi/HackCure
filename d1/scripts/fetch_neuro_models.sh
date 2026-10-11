#!/bin/sh
# Download the pretrained MediaPipe models used by the guided movement tests.
set -e
cd "$(dirname "$0")/../models" && mkdir -p mediapipe && cd mediapipe
base=https://storage.googleapis.com/mediapipe-models
for u in pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task \
         hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task \
         face_landmarker/face_landmarker/float16/latest/face_landmarker.task; do
  f=$(basename "$u")
  [ -s "$f" ] || curl -L --retry 3 -o "$f" "$base/$u"
done
ls -la
