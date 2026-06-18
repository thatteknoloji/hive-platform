/**
 * Hive Ultra Premium Plus - Main JavaScript
 */
(function () {
    'use strict';

    /* Light / dark tema */
    var themeToggle = document.getElementById('theme-toggle');
    var root = document.documentElement;
    var storedTheme = localStorage.getItem('hive-theme');

    function applyTheme(theme) {
        root.setAttribute('data-theme', theme);
        if (themeToggle) {
            themeToggle.textContent = theme === 'light' ? '☀️' : '🌙';
            themeToggle.setAttribute('aria-label', theme === 'light' ? 'Koyu temaya geç' : 'Açık temaya geç');
        }
    }

    if (storedTheme === 'light' || storedTheme === 'dark') {
        applyTheme(storedTheme);
    }

    /* Hero video — mobilde autoplay garantisi */
    var heroVideo = document.querySelector('.hero-video');
    if (heroVideo) {
        heroVideo.muted = true;
        heroVideo.setAttribute('playsinline', '');
        var playHero = function () {
            var p = heroVideo.play();
            if (p && typeof p.catch === 'function') {
                p.catch(function () {});
            }
        };
        playHero();
        document.addEventListener('visibilitychange', function () {
            if (!document.hidden) {
                playHero();
            }
        });
    }

    if (themeToggle) {
        themeToggle.addEventListener('click', function () {
            var next = root.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
            if (!root.getAttribute('data-theme')) {
                next = 'light';
            }
            applyTheme(next);
            localStorage.setItem('hive-theme', next);
        });
    }

    /* Mobile menu toggle */
    var menuToggle = document.querySelector('.menu-toggle');
    var navigation = document.querySelector('.main-navigation');

    if (menuToggle && navigation) {
        menuToggle.addEventListener('click', function () {
            var isOpen = navigation.classList.toggle('is-open');
            menuToggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
        });

        document.addEventListener('click', function (e) {
            if (!navigation.contains(e.target) && !menuToggle.contains(e.target)) {
                navigation.classList.remove('is-open');
                menuToggle.setAttribute('aria-expanded', 'false');
            }
        });
    }

    /* Phone reveal on single profile */
    var revealBtn = document.getElementById('reveal-phone');
    var phoneEl = document.getElementById('profile-phone');

    if (revealBtn && phoneEl) {
        revealBtn.addEventListener('click', function () {
            phoneEl.classList.add('revealed');
            revealBtn.style.display = 'none';
        });
    }

    /* İlan şeritleri — PHP klon yoksa JS ile tamamla */
    function initSlideMarquee() {
        document.querySelectorAll('.slide-container.slide-marquee[data-marquee="1"]').forEach(function (container) {
            var track = container.querySelector('.slide-track:not(.slide-track--clone)');
            var marqueeTrack = container.querySelector('.slide-marquee-track');
            if (!track || !marqueeTrack || track.children.length < 2) {
                return;
            }
            if (!marqueeTrack.querySelector('.slide-track--clone')) {
                var clone = track.cloneNode(true);
                clone.classList.add('slide-track--clone');
                clone.setAttribute('aria-hidden', 'true');
                marqueeTrack.appendChild(clone);
            }
            if (!container.style.getPropertyValue('--marquee-duration')) {
                var totalWidth = marqueeTrack.scrollWidth / 2;
                var duration = Math.max(28, Math.min(90, totalWidth / 42));
                container.style.setProperty('--marquee-duration', duration + 's');
            }
        });
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initSlideMarquee);
    } else {
        initSlideMarquee();
    }
    window.addEventListener('load', initSlideMarquee);

    /* Horizontal scroll with mouse wheel (marquee olmayan şeritler) */
    document.querySelectorAll('.slide-container:not(.slide-marquee)').forEach(function (container) {
        container.addEventListener('wheel', function (e) {
            if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) {
                e.preventDefault();
                container.scrollLeft += e.deltaY;
            }
        }, { passive: false });
    });

    /* Instagram hikayeler — yatay kaydırma (tekerlek + sürükle) */
    document.querySelectorAll('.stories-slider').forEach(function (slider) {
        var dragging = false;
        var startX = 0;
        var scrollStart = 0;
        var moved = false;

        slider.addEventListener('wheel', function (e) {
            if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) {
                e.preventDefault();
                slider.scrollLeft += e.deltaY;
            }
        }, { passive: false });

        slider.addEventListener('pointerdown', function (e) {
            if (e.button !== 0) {
                return;
            }
            dragging = true;
            moved = false;
            startX = e.clientX;
            scrollStart = slider.scrollLeft;
            slider.classList.add('is-dragging');
            if (slider.setPointerCapture) {
                slider.setPointerCapture(e.pointerId);
            }
        });

        slider.addEventListener('pointermove', function (e) {
            if (!dragging) {
                return;
            }
            var dx = e.clientX - startX;
            if (Math.abs(dx) > 5) {
                moved = true;
            }
            slider.scrollLeft = scrollStart - dx;
        });

        function endDrag() {
            dragging = false;
            slider.classList.remove('is-dragging');
            if (moved) {
                slider.dataset.dragged = '1';
                window.setTimeout(function () {
                    delete slider.dataset.dragged;
                }, 250);
            }
        }

        slider.addEventListener('pointerup', endDrag);
        slider.addEventListener('pointercancel', endDrag);
        slider.addEventListener('pointerleave', endDrag);

        slider.querySelectorAll('.story-item').forEach(function (btn) {
            btn.addEventListener('click', function (e) {
                if (slider.dataset.dragged) {
                    e.preventDefault();
                    e.stopImmediatePropagation();
                }
            }, true);
        });
    });

    /* Keyboard navigation for profile cards */
    document.querySelectorAll('.profile-card[role="button"]').forEach(function (card) {
        card.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                card.click();
            }
        });
    });

    /* Category horizontal scroll with wheel */
    document.querySelectorAll('.category-scroll, .category-poster-scroll, .nav-categories-scroll').forEach(function (el) {
        el.addEventListener('wheel', function (e) {
            if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) {
                e.preventDefault();
                el.scrollLeft += e.deltaY;
            }
        }, { passive: false });
    });

    /* Close mobile menu on category link click */
    document.querySelectorAll('.nav-categories-scroll a, .category-chip').forEach(function (link) {
        link.addEventListener('click', function () {
            if (navigation) {
                navigation.classList.remove('is-open');
            }
            if (menuToggle) {
                menuToggle.setAttribute('aria-expanded', 'false');
            }
        });
    });

    /* Story modal (Instagram-style) */
    var storyModal = document.getElementById('hive-story-modal');
    var storyImg = document.getElementById('hive-story-modal-img');
    var storyTitle = document.getElementById('hive-story-modal-title');
    var storyText = document.getElementById('hive-story-modal-text');
    var storyLoc = document.getElementById('hive-story-modal-location');
    var storyClose = storyModal ? storyModal.querySelector('.hive-story-modal-close') : null;
    var storyBackdrop = storyModal ? storyModal.querySelector('.hive-story-modal-backdrop') : null;

    function openStory(btn) {
        if (!storyModal) return;
        if (storyImg) storyImg.src = btn.getAttribute('data-story-image') || '';
        if (storyTitle) storyTitle.textContent = btn.getAttribute('data-story-title') || '';
        if (storyText) storyText.textContent = btn.getAttribute('data-story-text') || '';
        var loc = btn.getAttribute('data-story-location') || '';
        if (storyLoc) {
            storyLoc.textContent = loc ? '📍 ' + loc : '';
            storyLoc.style.display = loc ? 'block' : 'none';
        }
        storyModal.hidden = false;
        storyModal.setAttribute('aria-hidden', 'false');
        document.body.style.overflow = 'hidden';
    }

    function closeStory() {
        if (!storyModal) return;
        storyModal.hidden = true;
        storyModal.setAttribute('aria-hidden', 'true');
        document.body.style.overflow = '';
    }

    document.querySelectorAll('.story-item').forEach(function (btn) {
        btn.addEventListener('click', function () { openStory(btn); });
    });
    if (storyClose) storyClose.addEventListener('click', closeStory);
    if (storyBackdrop) storyBackdrop.addEventListener('click', closeStory);
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') closeStory();
    });

    /* Erotik hikaye beğeni */
    document.querySelectorAll('.story-like-btn').forEach(function (btn) {
        btn.addEventListener('click', function () {
            if (btn.classList.contains('liked') || typeof hiveUltra === 'undefined') return;
            var postId = btn.getAttribute('data-story-id');
            var countEl = btn.querySelector('.story-like-count');
            var fd = new FormData();
            fd.append('action', 'hive_story_like');
            fd.append('nonce', hiveUltra.nonce);
            fd.append('post_id', postId);
            fetch(hiveUltra.ajaxUrl, { method: 'POST', body: fd })
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    if (data.success && countEl) {
                        countEl.textContent = data.data.likes;
                        btn.classList.add('liked');
                    }
                });
        });
    });

    /* Kaydırma odağı — yalnızca dokunmatik (hover yok); masaüstünde ilanlar eşit kalır */
    function initMobileShowcaseFocus() {
        var containers = document.querySelectorAll('.slide-container, .category-poster-scroll');
        if (!containers.length) return;

        function pickFocusCard(container) {
            var items = container.querySelectorAll('.profile-card, .category-poster, .erotic-story-slide-card');
            if (!items.length) return;

            var box = container.getBoundingClientRect();
            var centerX = box.left + box.width / 2;
            var best = null;
            var bestDist = Infinity;

            items.forEach(function (el) {
                el.classList.remove('showcase-focus');
                var r = el.getBoundingClientRect();
                var mid = r.left + r.width / 2;
                var dist = Math.abs(mid - centerX);
                if (dist < bestDist) {
                    bestDist = dist;
                    best = el;
                }
            });

            if (best) {
                best.classList.add('showcase-focus');
            }
        }

        containers.forEach(function (container) {
            var scheduled = false;
            var hoverLock = false;

            container.querySelectorAll('.profile-card, .category-poster, .erotic-story-slide-card').forEach(function (el) {
                el.addEventListener('mouseenter', function () {
                    hoverLock = true;
                    container.querySelectorAll('.showcase-focus').forEach(function (f) {
                        f.classList.remove('showcase-focus');
                    });
                });
                el.addEventListener('mouseleave', function () {
                    hoverLock = false;
                    pickFocusCard(container);
                });
            });

            function update() {
                scheduled = false;
                if (!hoverLock) {
                    pickFocusCard(container);
                }
            }
            function onScroll() {
                if (!scheduled) {
                    scheduled = true;
                    requestAnimationFrame(update);
                }
            }
            container.addEventListener('scroll', onScroll, { passive: true });
            window.addEventListener('resize', onScroll);
            if (!hoverLock) {
                pickFocusCard(container);
            }
        });
    }

    if (window.matchMedia('(hover: none)').matches) {
        initMobileShowcaseFocus();
    }

    /* Kategori hamburger drawer */
    var catBtn = document.querySelector('.hive-cat-menu-btn');
    var catDrawer = document.getElementById('hive-cat-drawer');
    var catBackdrop = document.querySelector('.hive-cat-drawer-backdrop');

    function openCatDrawer() {
        if (!catDrawer) return;
        catDrawer.classList.add('is-open');
        catDrawer.setAttribute('aria-hidden', 'false');
        if (catBackdrop) {
            catBackdrop.hidden = false;
            catBackdrop.classList.add('is-visible');
        }
        if (catBtn) catBtn.setAttribute('aria-expanded', 'true');
        document.body.classList.add('hive-cat-drawer-open');
    }

    function closeCatDrawer() {
        if (!catDrawer) return;
        catDrawer.classList.remove('is-open');
        catDrawer.setAttribute('aria-hidden', 'true');
        if (catBackdrop) {
            catBackdrop.classList.remove('is-visible');
            catBackdrop.hidden = true;
        }
        if (catBtn) catBtn.setAttribute('aria-expanded', 'false');
        document.body.classList.remove('hive-cat-drawer-open');
    }

    if (catBtn && catDrawer) {
        catBtn.addEventListener('click', function () {
            if (catDrawer.classList.contains('is-open')) {
                closeCatDrawer();
            } else {
                openCatDrawer();
            }
        });
    }

    document.querySelectorAll('[data-hive-cat-close]').forEach(function (el) {
        el.addEventListener('click', closeCatDrawer);
    });

    document.querySelectorAll('.hive-cat-drawer a').forEach(function (link) {
        link.addEventListener('click', closeCatDrawer);
    });

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && catDrawer && catDrawer.classList.contains('is-open')) {
            closeCatDrawer();
        }
    });

    /* Accordion grupları */
    document.querySelectorAll('.hive-cat-group-toggle').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var group = btn.closest('.hive-cat-group');
            var body = group ? group.querySelector('.hive-cat-group-body') : null;
            if (!group || !body) return;
            var open = group.classList.toggle('is-open');
            btn.setAttribute('aria-expanded', open ? 'true' : 'false');
            if (open) {
                body.removeAttribute('hidden');
            } else {
                body.setAttribute('hidden', '');
            }
        });
    });

    /* Kategori arama */
    document.querySelectorAll('.hive-cat-search').forEach(function (input) {
        input.addEventListener('input', function () {
            var q = input.value.trim().toLowerCase();
            var panel = input.closest('[data-hive-cat-panel]');
            if (!panel) return;

            panel.querySelectorAll('[data-hive-cat-item]').forEach(function (item) {
                var hay = (item.getAttribute('data-search') || item.textContent || '').toLowerCase();
                item.classList.toggle('is-hidden', q.length > 0 && hay.indexOf(q) === -1);
            });

            if (q.length > 0) {
                panel.querySelectorAll('.hive-cat-group').forEach(function (group) {
                    var visible = group.querySelector('[data-hive-cat-item]:not(.is-hidden)');
                    var body = group.querySelector('.hive-cat-group-body');
                    var toggle = group.querySelector('.hive-cat-group-toggle');
                    if (visible && body && toggle) {
                        group.classList.add('is-open');
                        body.removeAttribute('hidden');
                        toggle.setAttribute('aria-expanded', 'true');
                    }
                });
            }
        });
    });

    /* Lazy loading fallback for older browsers */
    if (!('loading' in HTMLImageElement.prototype) && 'IntersectionObserver' in window) {
        var lazyImages = document.querySelectorAll('img[loading="lazy"]');
        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    var img = entry.target;
                    if (img.dataset.src) img.src = img.dataset.src;
                    observer.unobserve(img);
                }
            });
        });
        lazyImages.forEach(function (img) { observer.observe(img); });
    }

    /* Birleşik profil araması — canlı öneriler */
    var searchTimers = {};
    document.querySelectorAll('[data-hive-search-live="1"]').forEach(function (input) {
        var wrap = input.closest('.hive-unified-search');
        var dropdown = wrap ? wrap.querySelector('.hive-unified-search-dropdown') : null;
        if (!wrap || !dropdown || typeof hiveUltra === 'undefined') return;

        var i18n = hiveUltra.searchI18n || {};

        function hideDropdown() {
            dropdown.hidden = true;
            dropdown.innerHTML = '';
        }

        function renderItems(items, moreUrl) {
            if (!items.length) {
                dropdown.innerHTML = '<div class="hive-search-empty">' + (i18n.empty || 'Sonuç bulunamadı') + '</div>';
                dropdown.hidden = false;
                return;
            }
            var html = '<ul class="hive-search-results-list">';
            items.forEach(function (item) {
                html += '<li class="hive-search-result-item">';
                html += '<a href="' + item.url + '">';
                if (item.thumb) {
                    html += '<img src="' + item.thumb + '" alt="" width="48" height="48" loading="lazy">';
                }
                html += '<span class="hive-search-result-body">';
                html += '<strong>' + item.title + '</strong>';
                if (item.kategori) html += '<span class="hive-search-meta">' + item.kategori + '</span>';
                if (item.lokasyon) html += '<span class="hive-search-meta">📍 ' + item.lokasyon + '</span>';
                if (item.telegram) html += '<span class="hive-search-meta">@' + item.telegram.replace(/^@/, '') + '</span>';
                html += '</span></a></li>';
            });
            html += '</ul>';
            if (moreUrl) {
                html += '<a class="hive-search-more" href="' + moreUrl + '">' + (i18n.more || 'Tüm sonuçları gör') + ' →</a>';
            }
            dropdown.innerHTML = html;
            dropdown.hidden = false;
        }

        input.addEventListener('input', function () {
            var q = input.value.trim();
            var key = input.id || 'search';
            clearTimeout(searchTimers[key]);
            if (q.length < 2) {
                hideDropdown();
                return;
            }
            dropdown.innerHTML = '<div class="hive-search-loading">' + (i18n.loading || 'Aranıyor…') + '</div>';
            dropdown.hidden = false;
            searchTimers[key] = setTimeout(function () {
                var url = hiveUltra.ajaxUrl + '?action=hive_unified_search&nonce=' + encodeURIComponent(hiveUltra.nonce) + '&q=' + encodeURIComponent(q);
                fetch(url, { credentials: 'same-origin' })
                    .then(function (r) { return r.json(); })
                    .then(function (data) {
                        if (!data || !data.success) {
                            hideDropdown();
                            return;
                        }
                        renderItems(data.data.items || [], data.data.more || '');
                    })
                    .catch(function () { hideDropdown(); });
            }, 280);
        });

        input.addEventListener('blur', function () {
            setTimeout(hideDropdown, 200);
        });
        input.addEventListener('focus', function () {
            if (input.value.trim().length >= 2 && dropdown.innerHTML) {
                dropdown.hidden = false;
            }
        });
    });
})();
