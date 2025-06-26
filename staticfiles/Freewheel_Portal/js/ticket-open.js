const openBtn = document.getElementById('open-ticket-btn');
const pendingBtn = document.getElementById('pending-ticket-btn');
const onholdBtn = document.getElementById('onhold-ticket-btn');
const newBtn = document.getElementById('new-ticket-btn');
const unassignedBtn = document.getElementById('unassigned-ticket-btn')
const ticketContainer = document.getElementById('ticket-container');
const userContainer = document.getElementById('user-container');
const userFilter = document.getElementById('user-filter')
const ticketFilter = document.getElementById('ticket-filter')
 
let currentActive = null;
 
function resetButtons() {
  document.querySelectorAll('.stat-box').forEach(btn => {
    btn.classList.remove('active');
  });
}
 
function toggleSection(button) {
  const statusMap = {
    [openBtn?.id]: 'open',
    [pendingBtn?.id]: 'pending',
    [onholdBtn?.id]: 'hold',
    [newBtn?.id]: 'new',
    [unassignedBtn?.id]: 'unassigned'  // this is our special case
  };

  const selectedStatus = statusMap[button.id] || 'unassigned';

  if (currentActive === button) {
    ticketContainer.style.display = 'none';
    userContainer.style.display = 'block';
    ticketFilter.style.display = 'none';
    userFilter.style.display = 'block';
    resetButtons();
    currentActive = null;
  } else {
    ticketContainer.style.display = 'block';
    userContainer.style.display = 'none';
    ticketFilter.style.display = 'block';
    userFilter.style.display = 'none';
    resetButtons();
    button.classList.add('active');
    currentActive = button;

    // 🔁 Filter logic
    document.querySelectorAll('.ticket-row2').forEach(row => {
      const status = row.querySelector('.status-field')?.textContent.trim().toLowerCase();
      const assignee = row.querySelector('.assignee-field')?.textContent.trim().toLowerCase() || '';

if (selectedStatus === 'unassigned') {
  if ((assignee === '' || assignee === 'none') && status !== 'new') {
    row.style.display = '';
  } else {
    row.style.display = 'none';
  }
} else {
  if (status === selectedStatus) {
    row.style.display = '';
  } else {
    row.style.display = 'none';
  }
}

    });
  }
}
 

unassignedBtn?.addEventListener('click', () => toggleSection(unassignedBtn));

// Attach toggle listeners
openBtn?.addEventListener('click', () => toggleSection(openBtn));
pendingBtn?.addEventListener('click', () => toggleSection(pendingBtn));
onholdBtn?.addEventListener('click', () => toggleSection(onholdBtn));
newBtn?.addEventListener('click', () => toggleSection(newBtn));
 
// Dropdown menu functionality
document.addEventListener('DOMContentLoaded', () => {
  document.addEventListener('click', (e) => {
    const isMenuButton = e.target.classList.contains('menu-btn');
    const isInsideDropdown = e.target.closest('.dropdown-menu');
 
    if (isMenuButton) {
      const dropdown = e.target.nextElementSibling;
      document.querySelectorAll('.dropdown-menu').forEach(menu => {
        if (menu !== dropdown) menu.style.display = 'none';
      });
      dropdown.style.display = dropdown.style.display === 'flex' ? 'none' : 'flex';
    } else if (!isInsideDropdown) {
      document.querySelectorAll('.dropdown-menu').forEach(menu => {
        menu.style.display = 'none';
      });
    }
  });
 
  document.addEventListener('click', (e) => {
    if (e.target.classList.contains('comment-btn')) {
      const td = e.target.closest('td');
      td.querySelector('.comment-form').classList.remove('hidden');
      td.querySelector('.assign-form').classList.add('hidden');
    }
 
    if (e.target.classList.contains('assign-btn')) {
      const td = e.target.closest('td');
      td.querySelector('.assign-form').classList.remove('hidden');
      td.querySelector('.comment-form').classList.add('hidden');
    }
 
    if (e.target.classList.contains('submit-comment')) {
      const td = e.target.closest('td');
      const textarea = td.querySelector('textarea');
      const comment = textarea.value.trim();
      if (comment) {
        alert(`Comment submitted: ${comment}`);
        textarea.value = '';
        td.querySelector('.comment-form').classList.add('hidden');
      }
    }
 
    if (e.target.classList.contains('submit-assign')) {
      const td = e.target.closest('td');
      const assignee = td.querySelector('.assignee-dropdown').value;
      alert(`Ticket assigned to: ${assignee}`);
      td.querySelector('.assign-form').classList.add('hidden');
    }
  });
 
  document.querySelectorAll('.assignee-filter').forEach(input => {
    input.addEventListener('input', (e) => {
      const filter = e.target.value.toLowerCase();
      const select = e.target.nextElementSibling;
      Array.from(select.options).forEach(option => {
        option.style.display = option.text.toLowerCase().includes(filter) ? '' : 'none';
      });
    });
  });
});