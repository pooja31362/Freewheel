
document.addEventListener('DOMContentLoaded', function () {
    const container = document.querySelector('.container');
    const forgotBtn = document.getElementById('forgot-btn');
    const loginBtn = document.getElementById('login-btn');

    const forgotForm = document.getElementById('forget-form');
    const usernameInput = document.getElementById('username');
    const messageBox = document.getElementById('forgot-msg');
    const btn = forgotForm.querySelector('.btn');

    const loginForm = document.querySelector('.form-box.login form');
    const loginInputs = loginForm ? loginForm.querySelectorAll('input') : [];

    function getCSRFToken() {
        const cookie = document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='));
        return cookie ? cookie.split('=')[1] : null;
    }

    if (forgotBtn) {
        forgotBtn.addEventListener('click', () => {
            container.classList.add('active');
            usernameInput.value = '';
            messageBox.textContent = '';
            loginInputs.forEach(input => input.value = '');
        });
    }

    if (loginBtn) {
        loginBtn.addEventListener('click', () => {
            container.classList.remove('active');
            usernameInput.value = '';
            messageBox.textContent = '';
            loginInputs.forEach(input => input.value = '');
        });
    }

    if (forgotForm) {
        forgotForm.addEventListener('submit', async function (e) {
            e.preventDefault();

            const username = usernameInput.value.trim();
            const csrfToken = getCSRFToken();

            if (!username) {
                messageBox.textContent = 'Username is required.';
                messageBox.style.color = 'red';
                return;
            }

            // Show spinner effect
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending...';
            btn.disabled = true;
            btn.classList.add('sending');
            messageBox.textContent = '';

            const formData = new URLSearchParams();
            formData.append('username', username);

            try {
                const response = await fetch(forgotForm.action, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'X-CSRFToken': csrfToken
                    },
                    body: formData.toString()
                });

                const result = await response.text();

                // Reset button
                btn.innerHTML = 'GET EMAIL';
                btn.disabled = false;
                btn.classList.remove('sending');

                if (result === 'success') {
                    messageBox.textContent = 'MAIL HAS BEEN SUCCESSFULLY SENT TO YOUR INBOX';
                    messageBox.style.color = 'green';
                } else if (result === 'user_not_found') {
                    messageBox.textContent = 'NO USER FOUND';
                    messageBox.style.color = 'red';
                } else {
                    messageBox.textContent = 'Unexpected response.';
                    messageBox.style.color = 'red';
                }

            } catch (err) {
                btn.innerHTML = 'GET EMAIL';
                btn.disabled = false;
                btn.classList.remove('sending');

                messageBox.textContent = 'Something went wrong.';
                messageBox.style.color = 'red';
            }
        });
    }
});

