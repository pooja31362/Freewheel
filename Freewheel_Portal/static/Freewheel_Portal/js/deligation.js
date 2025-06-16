const del = document.getElementById('del');
const delBtn = document.getElementById('delBtn');
const wholePage = document.getElementById('wholePage');
const submitBtn = document.getElementById('delSubmit');
const click = document.getElementById('click')

let value = null

delBtn.addEventListener('click', () => {
    if(value == null){
        del.classList.add('active');
        wholePage.classList.add('active');
        value = 'active'; 
    }
    else{
        del.classList.remove('active');
        wholePage.classList.remove('active');
        value = null; 
    }
});

// ✅ Clicking Submit closes overlay
submitBtn.addEventListener('click', () => {
  setTimeout(() => {
    del.classList.remove('active');
    wholePage.classList.remove('active');
  }, 250);
  submitSection.innerHTML = `<div id="successMessage">✔️ Submitted successfully!</div>`;
});

// ✅ Click on blurred background closes prompt
click.addEventListener('click', (e) => {
  const isInsidePrompt = e.target.closest('.del');
  if (!isInsidePrompt) {
    del.classList.remove('active');
    wholePage.classList.remove('active');

  }
});

