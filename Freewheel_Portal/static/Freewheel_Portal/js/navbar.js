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

const statusBoxes = document.querySelectorAll('.status-box');
         
            statusBoxes.forEach(box => {
              box.addEventListener('click', () => {
                const selectedStatus = box.getAttribute('title');  // Always get the status
         
                // Reset styles on all
                statusBoxes.forEach(b => {
                  b.classList.remove('active');
                  b.style.backgroundColor = 'white';
                  b.style.color = 'black';
                });
         
                // Activate the clicked box
                const activeColor = box.getAttribute('data-color');
                box.classList.add('active');
                box.style.backgroundColor = activeColor;
                box.style.color = 'white';
         
                // 🔁 Always send the selected status to the server
                fetch("{% url 'home' %}", {
                  method: 'POST',
                  headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': '{{ csrf_token }}',
                  },
                  body: new URLSearchParams({
                    status: selectedStatus,
                  })
                })
                .then(res => {
                  if (!res.ok) throw new Error('Failed to update status');
                  console.log('Status updated to', selectedStatus);
                })
                .catch(err => {
                  console.error(err);
                });
              });
            });
