
document.addEventListener("DOMContentLoaded", function () {

  // Toggle three-dot menu
  document.querySelectorAll(".menu-btn").forEach(btn => {
    btn.addEventListener("click", function (e) {
      e.stopPropagation(); // Prevent closing when clicking the button
      const section = btn.closest(".menu-wrapper").querySelector(".dropdown-section");

      // Close all other dropdowns
      document.querySelectorAll(".dropdown-section").forEach(el => {
        if (el !== section) el.classList.add("hidden");
      });

      section.classList.toggle("hidden");
    });
  });

  // Comment button
  document.querySelectorAll(".comment-option").forEach(btn => {
    btn.addEventListener("click", function () {
      const row = btn.closest(".ticket-row");
      row.querySelector(".comment-box").classList.toggle("hidden");
      row.querySelector(".assign-box").classList.add("hidden");
      row.querySelector(".dropdown-section").classList.add("hidden");
    });
  });

  // Assign button
  document.querySelectorAll(".assign-option").forEach(btn => {
    btn.addEventListener("click", function () {
      const row = btn.closest(".ticket-row");
      row.querySelector(".assign-box").classList.toggle("hidden");
      row.querySelector(".comment-box").classList.add("hidden");
      row.querySelector(".dropdown-section").classList.add("hidden");
    });
  });

  // Submit comment
  document.querySelectorAll(".submit-comment").forEach(btn => {
    btn.addEventListener("click", function () {
      const row = btn.closest(".ticket-row");
      const ticketId = row.dataset.ticketId;
      const comment = row.querySelector("textarea").value.trim();

      if (!comment) return showToast("Comment cannot be empty.");

      fetch("{% url 'submit_comment' %}", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": "{{ csrf_token }}"
        },
        body: JSON.stringify({ ticket_id: ticketId, comment: comment })
      })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          showToast("Comment submitted!");
          row.querySelector(".comment-box").classList.add("hidden");
        } else {
          showToast("Failed to submit comment.");
        }
      });
    });
  });

  // Submit assign
  document.querySelectorAll(".submit-assign").forEach(btn => {
    btn.addEventListener("click", function () {
      const row = btn.closest(".ticket-row");
      const ticketId = row.dataset.ticketId;
      const assignee = row.querySelector(".assignee-dropdown").value;

      fetch("{% url 'assign_ticket' %}", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": "{{ csrf_token }}"
        },
        body: JSON.stringify({ ticket_id: ticketId, assignee_name: assignee })
      })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          showToast("Ticket assigned!");
          row.querySelector(".assign-box").classList.add("hidden");
          setTimeout(() => location.reload(), 1000);
        } else {
          showToast("Failed to assign.");
        }
      });
    });
  });

  // Filter assignees
  document.querySelectorAll(".assignee-filter").forEach(input => {
    input.addEventListener("input", function () {
      const filter = this.value.toLowerCase();
      const select = this.nextElementSibling;
      Array.from(select.options).forEach(option => {
        option.style.display = option.text.toLowerCase().includes(filter) ? "block" : "none";
      });
    });
  });

  // Prevent closing when clicking inside interactive areas
  document.querySelectorAll('.dropdown-section, .comment-box, .assign-box').forEach(el => {
    el.addEventListener('click', function (e) {
      e.stopPropagation();
    });
  });

  // Click outside to close all
  document.addEventListener('click', function () {
    document.querySelectorAll('.dropdown-section').forEach(el => el.classList.add('hidden'));
    document.querySelectorAll('.comment-box').forEach(el => el.classList.add('hidden'));
    document.querySelectorAll('.assign-box').forEach(el => el.classList.add('hidden'));
  });

});

// Toast Message
function showToast(message, duration = 3000) {
  let toast = document.getElementById("toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "toast";
    toast.style.position = "fixed";
    toast.style.bottom = "20px";
    toast.style.left = "50%";
    toast.style.transform = "translateX(-50%)";
    toast.style.backgroundColor = "#333";
    toast.style.color = "#fff";
    toast.style.padding = "10px 20px";
    toast.style.borderRadius = "5px";
    toast.style.zIndex = 9999;
    toast.style.transition = "opacity 0.3s";
    toast.classList.add("hidden");
    document.body.appendChild(toast);
  }

  toast.textContent = message;
  toast.classList.remove("hidden");
  toast.style.opacity = "1";

  setTimeout(() => {
    toast.style.opacity = "0";
    setTimeout(() => {
      toast.classList.add("hidden");
    }, 300); // match transition
  }, duration);
}
