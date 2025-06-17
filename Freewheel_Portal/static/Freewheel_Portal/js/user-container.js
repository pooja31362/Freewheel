document.addEventListener("DOMContentLoaded", function () {
  const ticketButtons = document.querySelectorAll(".ticketsList");

  ticketButtons.forEach((btn) => {
    btn.addEventListener("click", function () {
      const userCard = btn.closest(".user-card");
      const ticketSection = userCard.querySelector(".ticket");

      // Toggle visibility
      ticketSection.classList.toggle("active");
      userCard.classList.toggle("active");  // ✅ fix here
    });
  });
});

