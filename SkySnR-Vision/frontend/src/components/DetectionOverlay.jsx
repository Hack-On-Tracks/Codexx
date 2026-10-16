import { mediaUrl } from '../services/api';

// Boxes are stored in the original image's pixel space. The SVG uses the image's own
// pixel size as its viewBox, so boxes stay aligned however the image is resized in the browser.
export default function DetectionOverlay({ imageRef, width, height, detections = [], selectedId, onSelect, personClasses = ['person'] }) {
  if (!imageRef) return <div className="empty">No image available.</div>;
  return (
    <div className="evidence">
      <img src={mediaUrl(imageRef)} alt="Uploaded drone evidence" />
      {width && height && (
        <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" aria-label="Detection boxes">
          {detections.map((d) => {
            const b = d.bounding_box;
            const sel = selectedId === d.id;
            const cls = `box ${personClasses.includes(d.object_class.toLowerCase()) ? 'person' : ''} ${sel ? 'selected' : ''} ${selectedId && !sel ? 'dim' : ''}`;
            return (
              <g key={d.id} onClick={() => onSelect && onSelect(d.id)}>
                <rect className={cls} x={b.x} y={b.y} width={b.width} height={b.height}><title>{`${d.object_class} ${(d.confidence * 100).toFixed(0)}%`}</title></rect>
              </g>
            );
          })}
        </svg>
      )}
    </div>
  );
}
