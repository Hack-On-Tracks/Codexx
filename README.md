# SkySnr Vision
npm install && npm run dev   (build: npm run build)
Connect a real model: set VITE_DETECT_URL to an endpoint that accepts a multipart "file" and returns {detections:[{id,cls,conf,box:[x,y,w,h] normalized,...}]}.
Without it, only labelled demo detections are shown; uploads get no fake results.
Icons: lucide-react (MIT) plus custom SVG logo, class icons and map markers.
