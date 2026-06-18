/**
 * Hive Swipe — Tinder tarzı profil kaydırma
 */
(function () {
    'use strict';

    var cfg = window.hiveSwipeSettings || {};
    var STORAGE_SEEN = 'hive_swipe_seen';
    var STORAGE_LIKES = 'hive_swipe_likes';

    function getSeen() {
        try {
            return JSON.parse(localStorage.getItem(STORAGE_SEEN) || '[]');
        } catch (e) {
            return [];
        }
    }

    function addSeen(id) {
        var seen = getSeen();
        if (seen.indexOf(id) === -1) {
            seen.push(id);
            localStorage.setItem(STORAGE_SEEN, JSON.stringify(seen));
        }
    }

    function getLikes() {
        try {
            return JSON.parse(localStorage.getItem(STORAGE_LIKES) || '[]');
        } catch (e) {
            return [];
        }
    }

    function addLike(id) {
        var likes = getLikes();
        if (likes.indexOf(id) === -1) {
            likes.push(id);
            localStorage.setItem(STORAGE_LIKES, JSON.stringify(likes));
        }
    }

    function api(path, options) {
        options = options || {};
        var headers = {
            'Content-Type': 'application/json',
            'X-WP-Nonce': cfg.nonce || ''
        };
        return fetch((cfg.restUrl || '').replace(/\/$/, '') + path, {
            method: options.method || 'GET',
            headers: headers,
            credentials: 'same-origin',
            body: options.body ? JSON.stringify(options.body) : undefined
        }).then(function (r) {
            if (!r.ok) {
                return r.json().then(function (j) {
                    throw new Error(j.message || 'API error');
                });
            }
            return r.json();
        });
    }

    function SwipeApp(root) {
        this.root = root;
        this.profiles = [];
        this.index = 0;
        this.currentLike = null;
        this.dragging = false;
        this.startX = 0;
        this.currentX = 0;
        this.init();
    }

    SwipeApp.prototype.init = function () {
        this.renderShell();
        this.bindGlobal();
        this.loadProfiles();
    };

    SwipeApp.prototype.renderShell = function () {
        var i18n = cfg.i18n || {};
        this.root.innerHTML =
            '<div class="hive-swipe-wrap">' +
            '  <div class="hive-swipe-status" id="hive-swipe-status">' + (i18n.loading || '…') + '</div>' +
            '  <div class="hive-swipe-stack" id="hive-swipe-stack"></div>' +
            '  <div class="hive-swipe-actions">' +
            '    <button type="button" class="hive-swipe-btn hive-swipe-btn-nope" id="hive-btn-nope" aria-label="' + (i18n.dislike || 'Geç') + '">✕</button>' +
            '    <button type="button" class="hive-swipe-btn hive-swipe-btn-like" id="hive-btn-like" aria-label="' + (i18n.like || 'Beğen') + '">♥</button>' +
            '  </div>' +
            '  <div class="hive-swipe-offer-bar" id="hive-offer-bar" hidden>' +
            '    <p class="hive-swipe-offer-label">' + (i18n.offer || 'Teklif Yap') + '</p>' +
            '    <textarea id="hive-offer-text" rows="2" placeholder="' + (i18n.offerPlaceholder || '') + '"></textarea>' +
            '    <button type="button" class="btn btn-primary" id="hive-offer-send">' + (i18n.sendOffer || 'Gönder') + '</button>' +
            '  </div>' +
            '</div>';

        this.stack = document.getElementById('hive-swipe-stack');
        this.status = document.getElementById('hive-swipe-status');
        this.offerBar = document.getElementById('hive-offer-bar');
        this.offerText = document.getElementById('hive-offer-text');
    };

    SwipeApp.prototype.bindGlobal = function () {
        var self = this;
        document.getElementById('hive-btn-nope').addEventListener('click', function () {
            self.swipe('left');
        });
        document.getElementById('hive-btn-like').addEventListener('click', function () {
            self.swipe('right');
        });
        document.getElementById('hive-offer-send').addEventListener('click', function () {
            self.sendOffer();
        });
    };

    SwipeApp.prototype.loadProfiles = function () {
        var self = this;
        var exclude = getSeen().join(',');
        this.status.textContent = (cfg.i18n && cfg.i18n.loading) || '…';
        api('/next-profile?exclude=' + encodeURIComponent(exclude))
            .then(function (data) {
                self.profiles = self.profiles.concat(data.profiles || []);
                self.status.textContent = '';
                if (!self.getCurrent()) {
                    if (data.has_more) {
                        return self.loadProfiles();
                    }
                    self.showEmpty();
                } else {
                    self.renderCard();
                }
            })
            .catch(function () {
                self.status.textContent = (cfg.i18n && cfg.i18n.noProfiles) || 'Hata';
            });
    };

    SwipeApp.prototype.getCurrent = function () {
        return this.profiles[this.index] || null;
    };

    SwipeApp.prototype.showEmpty = function () {
        this.stack.innerHTML = '<div class="hive-swipe-empty">' + ((cfg.i18n && cfg.i18n.noProfiles) || '') + '</div>';
    };

    SwipeApp.prototype.renderCard = function () {
        var profile = this.getCurrent();
        if (!profile) {
            this.showEmpty();
            return;
        }
        var i18n = cfg.i18n || {};
        var vip = profile.vip ? '<span class="hive-swipe-vip">VIP</span>' : '';
        var price = profile.price ? '<p class="hive-swipe-price">' + profile.price + ' ₺</p>' : '';
        var age = profile.age ? ', ' + profile.age : '';

        this.stack.innerHTML =
            '<article class="hive-swipe-card" id="hive-active-card" data-id="' + profile.id + '">' +
            '  <a class="hive-swipe-card-link" href="' + profile.url + '">' +
            '    <img src="' + profile.image + '" alt="' + profile.name + '" loading="eager" decoding="async" />' +
            '  </a>' +
            '  <div class="hive-swipe-card-info">' + vip +
            '    <h2>' + profile.name + age + '</h2>' +
            '    <p class="hive-swipe-loc">📍 ' + profile.location + '</p>' + price +
            '    <a class="hive-swipe-view" href="' + profile.url + '">' + (i18n.viewProfile || 'Profil') + '</a>' +
            '  </div>' +
            '  <div class="hive-swipe-indicator hive-swipe-indicator-like">LIKE</div>' +
            '  <div class="hive-swipe-indicator hive-swipe-indicator-nope">NOPE</div>' +
            '</article>';

        this.offerBar.hidden = true;
        this.currentLike = null;
        this.bindCardDrag();
    };

    SwipeApp.prototype.bindCardDrag = function () {
        var self = this;
        var card = document.getElementById('hive-active-card');
        if (!card) return;

        var likeInd = card.querySelector('.hive-swipe-indicator-like');
        var nopeInd = card.querySelector('.hive-swipe-indicator-nope');

        function onStart(x) {
            self.dragging = true;
            self.startX = x;
            self.currentX = x;
            card.classList.add('is-dragging');
        }

        function onMove(x) {
            if (!self.dragging) return;
            self.currentX = x;
            var dx = x - self.startX;
            card.style.transform = 'translateX(' + dx + 'px) rotate(' + (dx * 0.05) + 'deg)';
            likeInd.style.opacity = Math.min(1, Math.max(0, dx / 120));
            nopeInd.style.opacity = Math.min(1, Math.max(0, -dx / 120));
        }

        function onEnd() {
            if (!self.dragging) return;
            self.dragging = false;
            card.classList.remove('is-dragging');
            var dx = self.currentX - self.startX;
            if (dx > 100) {
                self.swipe('right');
            } else if (dx < -100) {
                self.swipe('left');
            } else {
                card.style.transform = '';
                likeInd.style.opacity = 0;
                nopeInd.style.opacity = 0;
            }
        }

        card.addEventListener('mousedown', function (e) {
            if (e.target.closest('a')) return;
            e.preventDefault();
            onStart(e.clientX);
        });
        window.addEventListener('mousemove', function (e) {
            onMove(e.clientX);
        });
        window.addEventListener('mouseup', onEnd);

        card.addEventListener('touchstart', function (e) {
            if (e.target.closest('a')) return;
            onStart(e.touches[0].clientX);
        }, { passive: true });
        card.addEventListener('touchmove', function (e) {
            onMove(e.touches[0].clientX);
        }, { passive: true });
        card.addEventListener('touchend', onEnd);
    };

    SwipeApp.prototype.swipe = function (direction) {
        var profile = this.getCurrent();
        if (!profile) return;

        var card = document.getElementById('hive-active-card');
        var action = direction === 'right' ? 'like' : 'dislike';

        if (card) {
            card.classList.add(direction === 'right' ? 'swipe-out-right' : 'swipe-out-left');
        }

        addSeen(profile.id);

        api('/swipe', {
            method: 'POST',
            body: { profile_id: profile.id, action: action }
        }).then(function (res) {
            if (action === 'like') {
                addLike(profile.id);
                if (res.show_offer) {
                    this.showOfferBar(profile);
                }
            }
        }.bind(this)).catch(function () {});

        var self = this;
        setTimeout(function () {
            self.index += 1;
            if (!self.getCurrent() && self.profiles.length <= self.index) {
                self.loadProfiles();
            } else {
                self.renderCard();
            }
        }, 280);
    };

    SwipeApp.prototype.showOfferBar = function (profile) {
        this.currentLike = profile;
        this.offerBar.hidden = false;
        this.offerText.value = '';
        this.offerText.focus();
    };

    SwipeApp.prototype.sendOffer = function () {
        var profile = this.currentLike || this.getCurrent();
        if (!profile) return;
        var msg = (this.offerText.value || '').trim();
        if (msg.length < 3) return;

        var self = this;
        api('/offer', {
            method: 'POST',
            body: { profile_id: profile.id, message: msg }
        }).then(function () {
            self.offerBar.hidden = true;
            self.status.textContent = (cfg.i18n && cfg.i18n.offerSent) || 'OK';
            setTimeout(function () {
                self.status.textContent = '';
            }, 2500);
        }).catch(function () {});
    };

    document.addEventListener('DOMContentLoaded', function () {
        var root = document.getElementById('hive-swipe-app');
        if (root) {
            new SwipeApp(root);
        }
    });
})();
