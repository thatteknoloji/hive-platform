<?php
/**
 * Kuşadası Gece Hayatı — CPT + mahalle/saat/tür taxonomy
 *
 * @package Hive_Ultra_Premium
 */

if (!defined('ABSPATH')) {
    exit;
}

add_action('init', 'hive_register_gece_hayati');
function hive_register_gece_hayati() {
    register_taxonomy('gece_mahalle', array('gece_hayati'), array(
        'labels' => array(
            'name'          => __('Gece Mahalleleri', 'hive-ultra-premium'),
            'singular_name' => __('Mahalle', 'hive-ultra-premium'),
        ),
        'hierarchical'      => true,
        'public'            => true,
        'show_admin_column' => true,
        'rewrite'           => array('slug' => 'gece-mahalle'),
        'show_in_rest'      => true,
    ));

    register_taxonomy('gece_saat', array('gece_hayati'), array(
        'labels' => array(
            'name'          => __('Saat Dilimleri', 'hive-ultra-premium'),
            'singular_name' => __('Saat Dilimi', 'hive-ultra-premium'),
        ),
        'hierarchical'      => true,
        'public'            => true,
        'show_admin_column' => true,
        'rewrite'           => array('slug' => 'gece-saat'),
        'show_in_rest'      => true,
    ));

    register_taxonomy('gece_tur', array('gece_hayati'), array(
        'labels' => array(
            'name'          => __('Mekan Türleri', 'hive-ultra-premium'),
            'singular_name' => __('Mekan Türü', 'hive-ultra-premium'),
        ),
        'hierarchical'      => true,
        'public'            => true,
        'show_admin_column' => true,
        'rewrite'           => array('slug' => 'gece-tur'),
        'show_in_rest'      => true,
    ));

    register_post_type('gece_hayati', array(
        'labels' => array(
            'name'          => __('Gece Hayatı Rehberi', 'hive-ultra-premium'),
            'singular_name' => __('Mekan Rehberi', 'hive-ultra-premium'),
            'add_new_item'  => __('Yeni Mekan Rehberi', 'hive-ultra-premium'),
            'archives'      => __('Gece Hayatı Arşivi', 'hive-ultra-premium'),
        ),
        'public'              => true,
        'has_archive'         => true,
        'rewrite'             => array('slug' => 'gece-hayati'),
        'menu_icon'           => 'dashicons-palmtree',
        'supports'            => array('title', 'editor', 'thumbnail', 'excerpt'),
        'show_in_rest'        => true,
        'taxonomies'          => array('gece_mahalle', 'gece_saat', 'gece_tur'),
    ));
}

add_action('add_meta_boxes', 'hive_gece_hayati_metabox');
function hive_gece_hayati_metabox() {
    add_meta_box(
        'hive_gece_hayati_meta',
        __('Mekan Bilgileri', 'hive-ultra-premium'),
        'hive_gece_hayati_metabox_cb',
        'gece_hayati',
        'side',
        'default'
    );
}

function hive_gece_hayati_metabox_cb($post) {
    wp_nonce_field('hive_gece_hayati_save', 'hive_gece_hayati_nonce');
    $fields = array(
        'mekan_telefon'   => __('Telefon', 'hive-ultra-premium'),
        'mekan_instagram' => __('Instagram', 'hive-ultra-premium'),
        'mekan_adres'     => __('Adres', 'hive-ultra-premium'),
        'mekan_lat'       => __('Enlem', 'hive-ultra-premium'),
        'mekan_lon'       => __('Boylam', 'hive-ultra-premium'),
    );
    foreach ($fields as $key => $label) {
        $val = get_post_meta($post->ID, $key, true);
        echo '<p><label for="' . esc_attr($key) . '">' . esc_html($label) . '</label>';
        echo '<input type="text" id="' . esc_attr($key) . '" name="' . esc_attr($key) . '" value="' . esc_attr($val) . '" style="width:100%;margin-top:4px;"></p>';
    }
}

add_action('save_post_gece_hayati', 'hive_save_gece_hayati_meta');
function hive_save_gece_hayati_meta($post_id) {
    if (!isset($_POST['hive_gece_hayati_nonce']) || !wp_verify_nonce($_POST['hive_gece_hayati_nonce'], 'hive_gece_hayati_save')) {
        return;
    }
    if (defined('DOING_AUTOSAVE') && DOING_AUTOSAVE || !current_user_can('edit_post', $post_id)) {
        return;
    }
    foreach (array('mekan_telefon', 'mekan_instagram', 'mekan_adres', 'mekan_lat', 'mekan_lon') as $key) {
        if (isset($_POST[$key])) {
            update_post_meta($post_id, $key, sanitize_text_field(wp_unslash($_POST[$key])));
        }
    }
}

/**
 * İç linkleme — aynı mahalle / saat / tür rehberleri
 */
function hive_gece_related_posts($post_id = null, $limit = 6) {
    $post_id = $post_id ?: get_the_ID();
    $mahalle = wp_get_post_terms($post_id, 'gece_mahalle', array('fields' => 'ids'));
    $saat    = wp_get_post_terms($post_id, 'gece_saat', array('fields' => 'ids'));
    $tur     = wp_get_post_terms($post_id, 'gece_tur', array('fields' => 'ids'));

    $tax_query = array('relation' => 'OR');
    if ($mahalle) {
        $tax_query[] = array('taxonomy' => 'gece_mahalle', 'field' => 'term_id', 'terms' => $mahalle);
    }
    if ($saat) {
        $tax_query[] = array('taxonomy' => 'gece_saat', 'field' => 'term_id', 'terms' => $saat);
    }
    if ($tur) {
        $tax_query[] = array('taxonomy' => 'gece_tur', 'field' => 'term_id', 'terms' => $tur);
    }
    if (count($tax_query) < 2) {
        return array();
    }

    return get_posts(array(
        'post_type'      => 'gece_hayati',
        'posts_per_page' => $limit,
        'post__not_in'   => array($post_id),
        'tax_query'      => $tax_query,
        'orderby'        => 'rand',
    ));
}
