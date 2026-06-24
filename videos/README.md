# Videos Folder

This folder is for local input and output videos.

Recommended usage:

1. Put your own front-facing driving video here.
2. Run `code/tsr_demo.py` and save the annotated output here.
3. Keep large raw videos out of Git unless you explicitly want to version them.

Examples:

```bash
mkdir -p videos
cp /path/to/your/front_camera_video.mp4 videos/input.mp4
```

Smoke-test download:

```bash
mkdir -p videos
curl -L https://download.samplelib.com/mp4/sample-5s.mp4 -o videos/smoke_test.mp4
```

Note:

- `smoke_test.mp4` is only for pipeline verification.
- For meaningful TSR evaluation, use a real road-sign or dashcam video.
