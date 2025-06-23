document.addEventListener("DOMContentLoaded", function () {
  const ticketButtons = document.querySelectorAll(".ticketsList");

  ticketButtons.forEach((btn) => {
    btn.addEventListener("click", function () {
      const userCard = btn.closest(".user-card");
      const ticketSection = userCard.querySelector(".ticket");

      // Hide all other tickets and remove "active" class from other user-cards
      document.querySelectorAll(".ticket").forEach(t => {
        if (t !== ticketSection) t.classList.remove("active");
      });

      document.querySelectorAll(".user-card").forEach(card => {
        if (card !== userCard) card.classList.remove("active");
      });

      // Toggle the current one
      ticketSection.classList.toggle("active");
      userCard.classList.toggle("active");
    });
  });
});


