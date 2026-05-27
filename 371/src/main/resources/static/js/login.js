document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('.login-form');
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');
    const mfaInput = document.getElementById('mfaCode');

    form.addEventListener('submit', function(e) {
        const username = usernameInput.value.trim();
        const password = passwordInput.value;

        if (!username) {
            e.preventDefault();
            showError('请输入用户名');
            return;
        }

        if (!password) {
            e.preventDefault();
            showError('请输入密码');
            return;
        }

        if (mfaInput && mfaInput.value.trim()) {
            const mfaCode = mfaInput.value.trim();
            if (!/^\d{6}$/.test(mfaCode)) {
                e.preventDefault();
                showError('MFA验证码必须是6位数字');
                return;
            }
        }
    });

    function showError(message) {
        const existingAlert = document.querySelector('.alert-error');
        if (existingAlert) {
            existingAlert.remove();
        }

        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-error';
        alertDiv.textContent = message;

        const loginHeader = document.querySelector('.login-header');
        loginHeader.parentNode.insertBefore(alertDiv, form);

        setTimeout(() => {
            alertDiv.style.opacity = '0';
            setTimeout(() => alertDiv.remove(), 300);
        }, 5000);
    }

    usernameInput.addEventListener('input', function() {
        this.value = this.value.trim();
    });

    if (mfaInput) {
        mfaInput.addEventListener('input', function() {
            this.value = this.value.replace(/\D/g, '').slice(0, 6);
        });
    }
});
