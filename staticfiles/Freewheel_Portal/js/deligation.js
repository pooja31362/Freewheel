document.addEventListener('DOMContentLoaded', () => {
  const del = document.getElementById('del');
  const delBtn = document.getElementById('delBtn');
  const wholePage = document.getElementById('wholePage');
  const submitSection = document.getElementById('submitSection'); // optional
  let value = null;

  console.log("DOM fully loaded");
  console.log("del:", del);
  console.log("delBtn:", delBtn);
  console.log("wholePage:", wholePage);

  // Toggle popup
  delBtn?.addEventListener('click', () => {
    console.log("delBtn clicked");
    if (value === null) {
      del.classList.add('active');
      wholePage.classList.add('active');
      value = 'active';
      console.log("Popup opened");
    } else {
      del.classList.remove('active');
      wholePage.classList.remove('active');
      value = null;
      console.log("Popup closed");
    }
  });

  // Close popup on any shift submit
  ['submitShift1', 'submitShift3', 'submitShift6'].forEach(id => {
    const btn = document.getElementById(id);
    btn?.addEventListener('click', () => {
      console.log(`${id} clicked - closing popup`);
      setTimeout(() => {
        del.classList.remove('active');
        wholePage.classList.remove('active');
        value = null;
      }, 250);
    });
  });

  // Clicking anywhere outside #del closes it
  document.addEventListener('click', (e) => {
    const isInsideDel = e.target.closest('#del');
    const isDelBtn = e.target.closest('#delBtn');

    if (!isInsideDel && !isDelBtn && del.classList.contains('active')) {
      del.classList.remove('active');
      wholePage.classList.remove('active');
      value = null;
      console.log("Clicked outside - popup closed");
    }
  });
});
