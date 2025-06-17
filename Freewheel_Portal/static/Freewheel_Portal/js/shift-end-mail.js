
document.addEventListener("DOMContentLoaded", function () {
  const shiftMailBtn = document.getElementById("shiftMailBtn");
  const shiftMailDiv = document.getElementById("shift-end-mail");
  const userContainer = document.getElementById("user-container");

  shiftMailBtn.addEventListener("click", () => {
    // Hide the main content and show mail form
    userContainer.style.display = "none";
    shiftMailDiv.style.display = "block";
  });
});

