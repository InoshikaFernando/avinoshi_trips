// Handle missing images gracefully — show filename as placeholder
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.photo-slot img').forEach(function (img) {
    img.addEventListener('load', function () {
      img.closest('.photo-slot').style.borderStyle = 'solid';
      img.closest('.photo-slot').style.borderColor = 'var(--line)';
    });

    img.addEventListener('error', function () {
      img.style.display = 'none';
      var slot = img.closest('.photo-slot');
      var placeholder = document.createElement('div');
      placeholder.className = 'placeholder';
      placeholder.textContent = img.alt || 'Photo';
      slot.appendChild(placeholder);
    });

    // Handle already-cached images
    if (img.complete) {
      if (img.naturalWidth > 0) {
        img.closest('.photo-slot').style.borderStyle = 'solid';
        img.closest('.photo-slot').style.borderColor = 'var(--line)';
      } else {
        img.dispatchEvent(new Event('error'));
      }
    }
  });
});
