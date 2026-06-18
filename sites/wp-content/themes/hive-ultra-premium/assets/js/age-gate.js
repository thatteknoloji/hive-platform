/**
 * Hive — 18+ yaş doğrulama (oturum başına bir kez)
 */
(function () {
    'use strict';

    var cfg = window.hiveAgeGate || {};
    var key = cfg.storageKey || 'hive_age_verified';
    var gate = document.getElementById('hive-age-gate');
    var confirmBtn = document.getElementById('hive-age-confirm');
    var denyBtn = document.getElementById('hive-age-deny');
    var root = document.documentElement;

    if (!gate) {
        return;
    }

    function isVerified() {
        try {
            return sessionStorage.getItem(key) === '1';
        } catch (e) {
            return false;
        }
    }

    function lockPage() {
        root.classList.add('hive-age-pending');
        document.body.style.overflow = 'hidden';
        gate.hidden = false;
    }

    function unlockPage() {
        root.classList.remove('hive-age-pending');
        document.body.style.overflow = '';
        gate.hidden = true;
    }

    function verify() {
        try {
            sessionStorage.setItem(key, '1');
        } catch (e) {
            /* storage yoksa yine de kapat */
        }
        unlockPage();
    }

    function deny() {
        window.location.href = cfg.exitUrl || 'https://www.google.com/';
    }

    if (isVerified()) {
        gate.hidden = true;
        root.classList.remove('hive-age-pending');
        return;
    }

    lockPage();

    if (confirmBtn) {
        confirmBtn.addEventListener('click', verify);
    }

    if (denyBtn) {
        denyBtn.addEventListener('click', deny);
    }

    gate.addEventListener('keydown', function (e) {
        if (e.key === 'Tab' && gate.hidden === false) {
            var focusable = gate.querySelectorAll(
                'button:not([disabled]), a[href]'
            );
            if (!focusable.length) {
                return;
            }
            var first = focusable[0];
            var last = focusable[focusable.length - 1];
            if (e.shiftKey && document.activeElement === first) {
                e.preventDefault();
                last.focus();
            } else if (!e.shiftKey && document.activeElement === last) {
                e.preventDefault();
                first.focus();
            }
        }
    });

    window.setTimeout(function () {
        if (!gate.hidden && confirmBtn) {
            confirmBtn.focus();
        }
    }, 100);
})();
