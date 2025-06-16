document.addEventListener('DOMContentLoaded', function () {
  const agentFilter = document.getElementById('agent-filter');
  const shiftFilter = document.getElementById('shift-filter');
  const managerFilter = document.getElementById('manager-filter');
  const clearBtn = document.querySelector('.clear-filter p');
  const userCards = document.querySelectorAll('.user-card');
  const roleButtons = document.querySelectorAll('.button-group button');

  let selectedRoles = [];

  function applyFilters() {
    const selectedAgent = agentFilter.value;
    const selectedShift = shiftFilter.value;
    const selectedManager = managerFilter.value;

    userCards.forEach(card => {
      const agent = card.getAttribute('data-agent');
      const shift = card.getAttribute('data-shift');
      const manager = card.getAttribute('data-manager');
      const role = card.getAttribute('data-role');

      const roleMatch = selectedRoles.length === 0 || selectedRoles.includes(role);

      const show =
        (selectedAgent === 'All' || agent === selectedAgent) &&
        (selectedShift === 'All' || shift === selectedShift) &&
        (selectedManager === 'All' || manager === selectedManager) &&
        roleMatch;

      card.style.display = show ? 'block' : 'none';
    });
  }

  agentFilter.addEventListener('change', applyFilters);
  shiftFilter.addEventListener('change', applyFilters);
  managerFilter.addEventListener('change', applyFilters);

  roleButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const role = btn.textContent;

      // Toggle role in selectedRoles array
      if (selectedRoles.includes(role)) {
        selectedRoles = selectedRoles.filter(r => r !== role);
        btn.classList.remove('active');
      } else {
        selectedRoles.push(role);
        btn.classList.add('active');
      }

      applyFilters();
    });
  });

  clearBtn.addEventListener('click', () => {
    agentFilter.value = 'All';
    shiftFilter.value = 'All';
    managerFilter.value = 'All';
    selectedRoles = [];

    roleButtons.forEach(b => b.classList.remove('active'));
    applyFilters();
  });
});
