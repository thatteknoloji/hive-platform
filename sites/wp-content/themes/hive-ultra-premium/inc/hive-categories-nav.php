<?php
/**
 * Category navigation helpers
 *
 * @package Hive_Ultra_Premium
 */

if (!defined('ABSPATH')) {
    exit;
}

/**
 * Geçersiz (sayısal) kategori adlarını filtrele
 */
function hive_is_valid_category_term($term) {
    if (!$term || is_wp_error($term)) {
        return false;
    }
    $name = (string) $term->name;
    $slug = (string) $term->slug;
    if (preg_match('/^\d+$/', $name) || preg_match('/^\d+$/', $slug)) {
        return false;
    }
    if (preg_match('/^(escort|model|kategori|cat)\d+$/i', $slug)) {
        return false;
    }
    if (preg_match('/^\d+\s*-/', $name)) {
        return false;
    }
    return true;
}

/**
 * Kategoriler hub sayfası – yalnızca parent (mahalle)
 */
function hive_render_category_hub() {
    $parents = hive_get_valid_categories(array(
        'parent'     => 0,
        'hide_empty' => false,
        'orderby'    => 'name',
        'order'      => 'ASC',
    ));
    if (empty($parents)) {
        echo '<p>' . esc_html__('Henüz kategori tanımlanmamış.', 'hive-ultra-premium') . '</p>';
        return;
    }
    echo '<div class="category-hub-grid">';
    foreach ($parents as $term) {
        $link = get_term_link($term);
        if (is_wp_error($link)) {
            continue;
        }
        $child_count = count(hive_get_valid_categories(array('parent' => $term->term_id)));
        echo '<a class="category-hub-card" href="' . esc_url($link) . '">';
        echo '<h2 class="category-hub-name">' . esc_html($term->name) . '</h2>';
        echo '<span class="category-hub-meta">' . esc_html(sprintf(__('%d alt kategori', 'hive-ultra-premium'), $child_count)) . '</span>';
        echo '</a>';
    }
    echo '</div>';
}

/**
 * Parent kategori mi, alt kategorileri var mı?
 */
function hive_category_has_children($term_id) {
    return !empty(hive_get_valid_categories(array('parent' => (int) $term_id, 'number' => 1)));
}

/**
 * Alt ağaç göster (mahalle / cadde) — yaprakta profil listesi
 */
function hive_term_shows_child_tree($term) {
    if (!$term || is_wp_error($term)) {
        return false;
    }
    if (!hive_category_has_children($term->term_id)) {
        return false;
    }
    $group = get_term_meta($term->term_id, 'hive_cat_group', true);
    return in_array($group, array('mahalle', 'location'), true);
}

/**
 * Filtrelenmiş kategori listesi
 */
function hive_get_valid_categories($args = array()) {
    $defaults = array(
        'taxonomy'   => 'companion_category',
        'hide_empty' => false,
        'parent'     => 0,
        'orderby'    => 'count',
        'order'      => 'DESC',
        'number'     => 0,
    );
    $terms = get_terms(array_merge($defaults, $args));
    if (is_wp_error($terms) || empty($terms)) {
        return array();
    }
    return array_values(array_filter($terms, 'hive_is_valid_category_term'));
}

/**
 * Kategori için öne çıkan görsel URL
 */
function hive_category_poster_url($term_id) {
    $posts = get_posts(array(
        'post_type'      => 'companion_profile',
        'posts_per_page' => 1,
        'orderby'        => 'rand',
        'tax_query'      => array(
            array(
                'taxonomy' => 'companion_category',
                'field'    => 'term_id',
                'terms'    => $term_id,
            ),
        ),
        'meta_query'     => array(
            array('key' => '_thumbnail_id', 'compare' => 'EXISTS'),
        ),
    ));
    if ($posts && has_post_thumbnail($posts[0]->ID)) {
        return get_the_post_thumbnail_url($posts[0]->ID, 'hive-profile-card');
    }
    $any = get_posts(array(
        'post_type'      => 'companion_profile',
        'posts_per_page' => 1,
        'orderby'        => 'rand',
        'meta_query'     => array(array('key' => '_thumbnail_id', 'compare' => 'EXISTS')),
    ));
    if ($any && has_post_thumbnail($any[0]->ID)) {
        return get_the_post_thumbnail_url($any[0]->ID, 'hive-profile-card');
    }
    return hive_ultra_placeholder_url();
}

/**
 * Kategoriler sayfası URL
 */
function hive_categories_page_url() {
    $page = get_page_by_path('kategoriler');
    if ($page) {
        return get_permalink($page);
    }
    return home_url('/kategoriler/');
}
