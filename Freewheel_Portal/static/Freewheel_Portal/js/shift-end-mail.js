
document.addEventListener("DOMContentLoaded", function () {
  const shiftMailBtn = document.getElementById("shiftMailBtn");
  const shiftMailDiv = document.getElementById("shift-end-mail");
  const check = document.getElementById("check");

  shiftMailBtn.addEventListener("click", () => {
    // Hide the main content and show mail form
    check.style.display = "none";
    shiftMailDiv.style.display = "block";
  });
});

function copyTables() {
  const copyArea = document.getElementById("copyArea");
  const range = document.createRange();
  range.selectNode(copyArea);
  const selection = window.getSelection();
  selection.removeAllRanges();
  selection.addRange(range);
  try {
      document.execCommand("copy");
      alert("✅ Tables copied to clipboard!");
  } catch (err) {
      alert("❌ Copy failed. Please try manually.");
  }
  selection.removeAllRanges();
}