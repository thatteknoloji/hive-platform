<?php
/**
 * Multisite – ana site (balkutusu.com) bağlantıları
 *
 * @package Hive_Ultra_Premium
 */

if (!defined('ABSPATH')) {
    exit;
}

/**
 * Ana portal URL (network site #1)
 */
function hive_main_site_url() {
    if (is_multisite()) {
        return trailingslashit(get_site_url(1, '/'));
    }
    return trailingslashit(home_url('/'));
}

/**
 * Mevcut site ana site mi?
 */
function hive_is_main_site() {
    if (!is_multisite()) {
        return true;
    }
    return (int) get_current_blog_id() === 1;
}

/**
 * Subdomain sitelerde üst şerit – ana portala link
 */
function hive_render_main_site_bar() {
    if (hive_is_main_site()) {
        return;
    }
    $main = hive_main_site_url();
    ?>
    <div class="hive-main-site-bar" role="navigation" aria-label="<?php esc_attr_e('Ana portal', 'hive-ultra-premium'); ?>">
        <div class="container hive-main-site-bar-inner">
            <a href="<?php echo esc_url($main); ?>" class="hive-main-site-bar-logo" title="<?php esc_attr_e('Bal Kutusu Ana Site', 'hive-ultra-premium'); ?>">
                <img src="<?php echo esc_url(hive_brand_logo_url()); ?>" alt="Bal Kutusu" width="120" height="32" decoding="async" />
            </a>
            <span class="hive-main-site-bar-label"><?php esc_html_e('Kuşadası Escort Ana Portal', 'hive-ultra-premium'); ?></span>
            <a href="<?php echo esc_url($main); ?>" class="hive-main-site-bar-link">
                <?php esc_html_e('balkutusu.com', 'hive-ultra-premium'); ?> →
            </a>
        </div>
    </div>
    <?php
}
add_action('wp_body_open', 'hive_render_main_site_bar', 5);

/**
 * Footer ana site linki (subdomain)
 */
function hive_render_main_site_footer_link() {
    if (hive_is_main_site()) {
        return;
    }
    $main = hive_main_site_url();
    echo '<p class="hive-main-site-footer-link">';
    echo '<a href="' . esc_url($main) . '">← ' . esc_html__('Bal Kutusu Ana Site', 'hive-ultra-premium') . ' (balkutusu.com)</a>';
    echo '</p>';
}
