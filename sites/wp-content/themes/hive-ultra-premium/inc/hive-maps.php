<?php
/**
 * Google Maps (super-simple-map-embeds uyumlu iframe)
 *
 * @package Hive_Ultra_Premium
 */

if (!defined('ABSPATH')) {
    exit;
}

/**
 * Google Maps iframe (eklenti bloğu ile aynı URL yapısı)
 */
function hive_render_map_iframe($address, $zoom = 14, $height = 350) {
    $address = trim((string) $address);
    if ($address === '') {
        return;
    }

    $src = 'https://maps.google.com/maps?q=' . rawurlencode($address) . '&hl=tr&output=embed&z=' . (int) $zoom;
    $height = max(200, (int) $height);

    echo '<div class="hive-map-embed" style="position:relative;padding-bottom:56.25%;height:0;overflow:hidden;border-radius:16px;">';
    echo '<iframe src="' . esc_url($src) . '" style="position:absolute;top:0;left:0;width:100%;height:100%;border:0;" loading="lazy" allowfullscreen aria-hidden="false" tabindex="0" title="' . esc_attr($address) . '"></iframe>';
    echo '</div>';
}

/**
 * Profil sayfası haritası (lokasyon meta varsa)
 */
function hive_render_profile_map($post_id = null) {
    $post_id = $post_id ? (int) $post_id : get_the_ID();
    if (!$post_id) {
        return;
    }

    $location = get_post_meta($post_id, 'lokasyon', true);
    if (empty($location)) {
        return;
    }

    $address = (stripos($location, 'kuşadası') !== false || stripos($location, 'kusadasi') !== false)
        ? $location
        : 'Kuşadası ' . $location;

    echo '<section class="profile-map-container">';
    echo '<h3 class="map-title">📍 ' . esc_html($location) . ' konumu</h3>';
    hive_render_map_iframe($address, 15, 300);
    echo '<p class="map-caption">' . esc_html__('Haritada gösterilen yakın çevredeki oteller, plajlar ve ulaşım bilgileri.', 'hive-ultra-premium') . '</p>';
    echo '</section>';
}

/**
 * Kategori (companion_category) sayfası haritası
 */
function hive_render_category_map() {
    if (!is_tax('companion_category')) {
        return;
    }

    $term = get_queried_object();
    if (!$term || empty($term->name)) {
        return;
    }

    $address = 'Kuşadası ' . $term->name;

    echo '<section class="category-map-container">';
    echo '<h3 class="map-title">📍 ' . esc_html($term->name) . ' konumu</h3>';
    hive_render_map_iframe($address, 14, 350);
    echo '<p class="map-caption">' . esc_html__('Yakın çevredeki oteller, plajlar ve ulaşım bilgileri için haritayı kullanabilirsiniz.', 'hive-ultra-premium') . '</p>';
    echo '</section>';
}
