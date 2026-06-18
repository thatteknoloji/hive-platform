<?php
/**
 * Ana site (blog 1) ilan feed'i – tüm subdomainlerde aynı profiller
 *
 * @package Hive_Ultra_Premium
 */

if (!defined('ABSPATH')) {
    exit;
}

/**
 * Subdomain başlık etiketi (anal.balkutusu.com → Anal)
 */
function hive_subdomain_label() {
    if (!is_multisite() || hive_is_main_site()) {
        return '';
    }
    $details = get_blog_details(get_current_blog_id());
    if (!$details || empty($details->domain)) {
        return get_bloginfo('name');
    }
    $slug = str_replace('.balkutusu.com', '', $details->domain);
    return ucwords(str_replace('-', ' ', $slug));
}

/**
 * Ana sitedeki profil arşiv URL
 */
function hive_main_profiles_archive_url() {
    if (!is_multisite() || hive_is_main_site()) {
        return get_post_type_archive_link('companion_profile');
    }
    switch_to_blog(1);
    $url = get_post_type_archive_link('companion_profile');
    restore_current_blog();
    return $url;
}

/**
 * Ana site blogunda çalıştır (subdomainde ilanlar blog 1'den gelir)
 */
function hive_on_main_blog_for_feed($callback) {
    $switched = false;
    if (is_multisite() && !hive_is_main_site()) {
        switch_to_blog(1);
        $switched = true;
    }
    $callback();
    if ($switched) {
        restore_current_blog();
    }
}

/**
 * Ana sayfa profil slider'ları – VIP, Popüler, Yeni, 2'li, 3'lü
 */
function hive_render_home_profile_feed() {
    hive_on_main_blog_for_feed(function () {
        get_template_part('template-parts/home', 'profile-feed');
    });
}
