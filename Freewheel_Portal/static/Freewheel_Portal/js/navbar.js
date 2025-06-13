// ../../static/Freewheel_Portal/js/navbar.js

function toggleMenu() {
  const navLinks = document.getElementById('navLinks');
  navLinks.classList.toggle('active');
}

// Close mobile menu when window is resized to desktop
window.addEventListener('resize', () => {
  const navLinks = document.getElementById('navLinks');
  if (window.innerWidth > 768) {
    navLinks.classList.remove('active');
  }
});
