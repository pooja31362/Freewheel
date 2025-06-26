document.addEventListener('DOMContentLoaded', function () {
  // ===== USER FILTERS =====
  const agentFilter = document.getElementById('agent-filter');
  const shiftFilter = document.getElementById('shift-filter');
  const managerFilter = document.getElementById('manager-filter');
  const userStatus = document.getElementById('region-filter');
  const userClearBtn = document.querySelector('#user-filter .clear-filter p');
  const userCards = document.querySelectorAll('.user-card');
  const roleButtons = document.querySelectorAll('#user-filter .button-group button');
  let selectedRoles = [];
  let selectedaccess = [];


  function applyUserFilters() {
    const selectedAgent = agentFilter.value;
    const selectedShift = shiftFilter.value;
    const selectedManager = managerFilter.value;
    const selectedStatus = userStatus.value;

    userCards.forEach(card => {
      const agent = card.getAttribute('data-agent');
      const shift = card.getAttribute('data-shift');
      const manager = card.getAttribute('data-manager');
      const role = card.getAttribute('data-role');
      const status = card.getAttribute('data-status');
      const access = card.getAttribute('data-access');

      const roleMatch = selectedRoles.length === 0 || selectedRoles.includes(role);
      const accessMatch = selectedaccess.length === 0 || selectedaccess.includes(access.toLowerCase());


      const show =
        (selectedAgent === 'All' || agent === selectedAgent) &&
        (selectedShift === 'All' || shift === selectedShift) &&
        (selectedManager === 'All' || manager === selectedManager) &&
        (selectedStatus === 'All' || status === selectedStatus) &&
        roleMatch &&
        accessMatch;

      card.style.display = show ? 'block' : 'none';
    });
  }

  agentFilter?.addEventListener('change', applyUserFilters);
  shiftFilter?.addEventListener('change', applyUserFilters);
  managerFilter?.addEventListener('change', applyUserFilters);
  userStatus?.addEventListener('change', applyUserFilters);

// Role button filtering
roleButtons.forEach(btn => {
  btn.addEventListener('click', () => {
    const role = btn.dataset.role;
    if (role) {
      if (selectedRoles.includes(role)) {
        selectedRoles = selectedRoles.filter(r => r !== role);
        btn.classList.remove('active');
      } else {
        selectedRoles.push(role);
        btn.classList.add('active');
      }
    }

    const access = btn.dataset.access;
    if (access) {
      if (selectedaccess.includes(access)) {
        selectedaccess = selectedaccess.filter(a => a !== access);
        btn.classList.remove('active');
      } else {
        selectedaccess.push(access);
        btn.classList.add('active');
      }
    }

    applyUserFilters();
  });
});


  userClearBtn?.addEventListener('click', () => {
    agentFilter.value = 'All';
    shiftFilter.value = 'All';
    managerFilter.value = 'All';
    userStatus.value = 'All';
    selectedRoles = [];
    selectedaccess = [];
    roleButtons.forEach(b => b.classList.remove('active'));

    applyUserFilters();
  });

  // ===== TICKET FILTERS =====
  const ticketIdInput = document.getElementById('ticket-id');
  const ticketAssignee = document.getElementById('ticket-assignee');
  const ticketGroup = document.getElementById('ticket-group');
  const ticketPriority = document.querySelector('#ticket-filter select:nth-of-type(3)');
  const ticketManager = document.querySelector('#ticket-filter select:nth-of-type(4)');
  const clearTicketFilter = document.querySelector('#ticket-filter .clear-filter p');
  const ticketCards = document.querySelectorAll('.ticket-card');

  function applyTicketFilters() {
    const idFilter = ticketIdInput.value.trim();
    const assigneeFilter = ticketAssignee.value;
    const groupFilter = ticketGroup.value;
    const priorityFilter = ticketPriority.value;
    const managerFilter = ticketManager.value;

    ticketCards.forEach(card => {
      const cardId = card.getAttribute('data-ticket-id');
      const cardAssignee = card.getAttribute('data-assignee-name');
      const cardGroup = card.getAttribute('data-product');
      const cardPriority = card.getAttribute('data-priority');
      const cardManager = card.getAttribute('data-manager');

      const matchesId = idFilter === '' || cardId === idFilter;
      const matchesAssignee = assigneeFilter === '' || cardAssignee === assigneeFilter;
      const matchesGroup = groupFilter === '' || cardGroup === groupFilter;
      const matchesPriority = priorityFilter === '' || cardPriority === priorityFilter;
      const matchesManager = managerFilter === '' || cardManager === managerFilter;

      const show = matchesId && matchesAssignee && matchesGroup && matchesPriority && matchesManager;
      card.style.display = show ? 'block' : 'none';
    });
  }

  ticketIdInput?.addEventListener('input', applyTicketFilters);
  ticketAssignee?.addEventListener('change', applyTicketFilters);
  ticketGroup?.addEventListener('change', applyTicketFilters);
  ticketPriority?.addEventListener('change', applyTicketFilters);
  ticketManager?.addEventListener('change', applyTicketFilters);

  clearTicketFilter?.addEventListener('click', () => {
    ticketIdInput.value = '';
    ticketAssignee.selectedIndex = 0;
    ticketGroup.selectedIndex = 0;
    ticketPriority.selectedIndex = 0;
    ticketManager.selectedIndex = 0;
    applyTicketFilters();
  });
});