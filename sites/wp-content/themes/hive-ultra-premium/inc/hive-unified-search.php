<?php
/**
 * Birleşik profil araması — ilan adı, telegram, kategori, lokasyon, özellikler
 *
 * @package Hive_Ultra_Premium
 */

if (!defined('ABSPATH')) {
    exit;
}

/** Aranacak profil meta alanları */
function hive_search_meta_keys() {
    return array('telegram', 'telefon', 'lokasyon', 'ozellikler', 'hizmetler', 'fiyat', 'odeme_sekli', 'yas');
}

add_action('pre_get_posts', 'hive_unified_search_pre_get_posts', 20);
function hive_unified_search_pre_get_posts($query) {
    if (is_admin() || !$query->is_main_query() || !$query->is_search()) {
        return;
    }
    $query->set('post_type', array('companion_profile'));
    $query->set('hive_unified_search', true);
}

add_filter('posts_join', 'hive_unified_search_join', 10, 2);
function hive_unified_search_join($join, $query) {
    if (empty($query->query_vars['hive_unified_search'])) {
        return $join;
    }
    global $wpdb;
    $join .= " LEFT JOIN {$wpdb->postmeta} AS hive_pm ON ({$wpdb->posts}.ID = hive_pm.post_id) ";
    $join .= " LEFT JOIN {$wpdb->term_relationships} AS hive_tr ON ({$wpdb->posts}.ID = hive_tr.object_id) ";
    $join .= " LEFT JOIN {$wpdb->term_taxonomy} AS hive_tt ON (hive_tr.term_taxonomy_id = hive_tt.term_taxonomy_id AND hive_tt.taxonomy = 'companion_category') ";
    $join .= " LEFT JOIN {$wpdb->terms} AS hive_t ON (hive_tt.term_id = hive_t.term_id) ";
    return $join;
}

add_filter('posts_search', 'hive_unified_search_where', 10, 2);
function hive_unified_search_where($search, $query) {
    if (empty($query->query_vars['hive_unified_search'])) {
        return $search;
    }
    global $wpdb;
    $term = $query->get('s');
    if (!$term) {
        return $search;
    }

    $like = '%' . $wpdb->esc_like($term) . '%';
    $meta_in = "'" . implode("','", array_map('esc_sql', hive_search_meta_keys())) . "'";

    $custom = $wpdb->prepare(
        " OR ({$wpdb->posts}.post_title LIKE %s)
           OR ({$wpdb->posts}.post_content LIKE %s)
           OR ({$wpdb->posts}.post_excerpt LIKE %s)
           OR (hive_pm.meta_key IN ($meta_in) AND hive_pm.meta_value LIKE %s)
           OR (hive_t.name LIKE %s)
           OR (hive_t.slug LIKE %s) ",
        $like,
        $like,
        $like,
        $like,
        $like,
        $like
    );

    if (preg_match('/^\(\s*(.+)\s*\)$/', $search, $m)) {
        $search = '(' . $m[1] . $custom . ')';
    } else {
        $search = '(' . ltrim($search, ' AND') . $custom . ')';
    }
    return $search;
}

add_filter('posts_distinct', 'hive_unified_search_distinct', 10, 2);
function hive_unified_search_distinct($distinct, $query) {
    if (!empty($query->query_vars['hive_unified_search'])) {
        return 'DISTINCT';
    }
    return $distinct;
}

add_filter('posts_groupby', 'hive_unified_search_groupby', 10, 2);
function hive_unified_search_groupby($groupby, $query) {
    if (empty($query->query_vars['hive_unified_search'])) {
        return $groupby;
    }
    global $wpdb;
    return "{$wpdb->posts}.ID";
}

/**
 * Canlı arama (AJAX)
 */
add_action('wp_ajax_hive_unified_search', 'hive_ajax_unified_search');
add_action('wp_ajax_nopriv_hive_unified_search', 'hive_ajax_unified_search');
function hive_ajax_unified_search() {
    check_ajax_referer('hive_ultra_nonce', 'nonce');

    $q = isset($_GET['q']) ? sanitize_text_field(wp_unslash($_GET['q'])) : '';
    if (strlen($q) < 2) {
        wp_send_json_success(array('items' => array(), 'total' => 0));
    }

    $args = array(
        'post_type'              => 'companion_profile',
        'post_status'            => 'publish',
        'posts_per_page'         => 12,
        's'                      => $q,
        'hive_unified_search'    => true,
        'suppress_filters'       => true,
    );

    add_filter('posts_join', 'hive_unified_search_join', 10, 2);
    add_filter('posts_search', 'hive_unified_search_where', 10, 2);
    add_filter('posts_distinct', 'hive_unified_search_distinct', 10, 2);
    add_filter('posts_groupby', 'hive_unified_search_groupby', 10, 2);

    $posts = get_posts($args);

    remove_filter('posts_join', 'hive_unified_search_join', 10);
    remove_filter('posts_search', 'hive_unified_search_where', 10);
    remove_filter('posts_distinct', 'hive_unified_search_distinct', 10);
    remove_filter('posts_groupby', 'hive_unified_search_groupby', 10);

    $items = array();
    foreach ($posts as $post) {
        $cats = get_the_terms($post->ID, 'companion_category');
        $cat_names = array();
        if ($cats && !is_wp_error($cats)) {
            foreach ($cats as $c) {
                $cat_names[] = $c->name;
            }
        }
        $thumb = get_the_post_thumbnail_url($post->ID, 'hive-profile-thumb');
        if (!$thumb && function_exists('hive_ultra_placeholder_url')) {
            $thumb = hive_ultra_placeholder_url();
        }
        $items[] = array(
            'id'        => $post->ID,
            'title'     => get_the_title($post->ID),
            'url'       => get_permalink($post->ID),
            'thumb'     => $thumb,
            'lokasyon'  => hive_ultra_get_meta($post->ID, 'lokasyon'),
            'telegram'  => hive_ultra_get_meta($post->ID, 'telegram'),
            'fiyat'     => hive_ultra_get_meta($post->ID, 'fiyat'),
            'kategori'  => implode(', ', $cat_names),
        );
    }

    wp_send_json_success(array(
        'items' => $items,
        'total' => count($items),
        'more'  => add_query_arg(
            array('s' => $q, 'post_type' => 'companion_profile'),
            home_url('/')
        ),
    ));
}

/**
 * Arama formu render
 */
function hive_render_unified_search($args = array()) {
    $defaults = array(
        'id'          => 'hive-unified-search',
        'placeholder' => __('İlan adı, kullanıcı adı, kategori, lokasyon ara…', 'hive-ultra-premium'),
        'class'       => 'hive-unified-search',
        'live'        => true,
        'compact'     => false,
    );
    $args = wp_parse_args($args, $defaults);
    get_template_part('template-parts/unified', 'search', $args);
}
