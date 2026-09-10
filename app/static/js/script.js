// app/static/js/script.js

(function () {
    'use strict';

    // Warn about emergency symptoms as the user types, before they submit.
    // The server runs the authoritative check; this is only a faster nudge.
    var EMERGENCY_HINTS = [
        'chest pain', 'cant breathe', 'can not breathe', 'cannot breathe',
        'difficulty breathing', 'trouble breathing', 'unconscious',
        'severe bleeding', 'coughing blood', 'seizure', 'slurred speech'
    ];

    var textarea = document.getElementById('symptoms');
    if (!textarea) {
        return;
    }

    var notice = document.createElement('p');
    notice.className = 'warning-note';
    notice.hidden = true;
    notice.textContent =
        'What you have described may be a medical emergency. Do not wait for ' +
        'this app - call Rescue 1122 or go to the nearest hospital now.';
    textarea.parentNode.insertBefore(notice, textarea.nextSibling);

    textarea.addEventListener('input', function () {
        var value = textarea.value.toLowerCase();
        notice.hidden = !EMERGENCY_HINTS.some(function (hint) {
            return value.indexOf(hint) !== -1;
        });
    });
})();
