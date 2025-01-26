function animateText(text) {
  const container = document.querySelector('.mentat-litany');
  if (!container) return;

  container.innerHTML = '';
  container.classList.remove('visible');

  // Add characters with delay
  [...text].forEach((char, i) => {
      const span = document.createElement('span');
      span.textContent = char;
      span.className = 'char';
      span.style.animationDelay = `${i * 50}ms`;
      container.appendChild(span);
  });

  // Show container
  requestAnimationFrame(() => {
      container.classList.add('visible');
  });
}

function fadeOutPreviousResults() {
  const containers = document.querySelectorAll('.grid-container');
  containers.forEach(container => {
      container.classList.add('fade-out');
      setTimeout(() => {
          container.remove();
      }, 300); // Match transition duration
  });
}

// Expose the function globally for Streamlit to call
window.fadeOutPreviousResults = fadeOutPreviousResults;